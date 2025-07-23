#!/usr/bin/env python3
"""
Event-driven script to connect to browser context and add overlay to existing pages.
No polling loops - uses event listeners instead.
"""

import asyncio
import requests
import json
from playwright.async_api import async_playwright


async def add_overlay_to_existing_pages_event_driven(cdp_endpoint: str, page_index: int = 0):
    """
    Connect to existing browser and add overlay to existing pages using event-driven approach.
    
    Args:
        cdp_endpoint: CDP endpoint like http://localhost:9222
        page_index: Index of the page to add overlay to (default: 0)
    """
    print(f"Connecting to browser at: {cdp_endpoint}")
    
    try:
        # Get WebSocket URL from CDP endpoint
        cdp_endpoint = cdp_endpoint.rstrip('/')
        version_url = f"{cdp_endpoint}/json/version"
        response = requests.get(version_url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            browser_ws_url = data.get('webSocketDebuggerUrl')
            print(f"Browser WebSocket URL: {browser_ws_url}")
            
            # Connect to browser
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(browser_ws_url)
                print("✅ Successfully connected to existing browser")
                
                # Get browser context
                contexts = browser.contexts
                if not contexts:
                    print("❌ No browser contexts found")
                    return
                
                context = contexts[0]  # Use the first context
                print(f"Using browser context: {context}")
                
                # Get existing pages
                pages = context.pages
                print(f"Found {len(pages)} existing pages:")
                
                for i, page in enumerate(pages):
                    print(f"  Page {i}: {page.url}")
                
                if page_index >= len(pages):
                    print(f"❌ Page index {page_index} not found. Available pages: {len(pages)}")
                    return
                
                # Get the target page
                target_page = pages[page_index]
                print(f"\n🎯 Adding overlay to page {page_index}: {target_page.url}")
                
                # Store captured elements
                captured_elements = []
                # current_page_index = page_index
                
                # Set up console message listener
                async def handle_console(msg):
                    if msg.type == 'log' and 'XPath captured:' in msg.text:
                        try:
                            # Extract XPath data from console message
                            xpath_data = msg.text.split('XPath captured: ')[1]
                            element_data = json.loads(xpath_data)
                            captured_elements.append(element_data)
                            print("\n🎯 Captured element:")
                            print(f"  Tag: {element_data['tagName']}")
                            print(f"  XPath: {element_data['xpath']}")
                            if element_data.get('textContent'):
                                print(f"  Text: {element_data['textContent'][:50]}...")
                        except Exception as e:
                            print(f"Error parsing XPath data: {e}")
                
                # Listen for console messages
                target_page.on('console', handle_console)
                
                # Add overlay CSS and JavaScript
                await target_page.add_init_script("""
                    // Create overlay styles
                    const style = document.createElement('style');
                    style.textContent = `
                        .element-overlay {
                            position: fixed;
                            top: 0;
                            left: 0;
                            width: 100%;
                            height: 100%;
                            background: rgba(0, 0, 0, 0.3);
                            z-index: 999999;
                            pointer-events: auto;
                            cursor: crosshair;
                            border: 2px solid red;
                        }
                        .element-highlight {
                            position: absolute;
                            border: 3px solid #ff0000;
                            background: rgba(255, 0, 0, 0.3);
                            pointer-events: none;
                            transition: all 0.2s ease;
                        }
                        .element-highlight:hover {
                            border-color: #00ff00;
                            background: rgba(0, 255, 0, 0.4);
                        }
                        .element-info {
                            position: absolute;
                            background: rgba(0, 0, 0, 0.9);
                            color: white;
                            padding: 8px;
                            border-radius: 5px;
                            font-size: 14px;
                            white-space: nowrap;
                            z-index: 1000000;
                            pointer-events: none;
                            border: 1px solid white;
                        }
                        .overlay-controls {
                            position: fixed;
                            top: 10px;
                            right: 10px;
                            background: rgba(0, 0, 0, 0.8);
                            color: white;
                            padding: 10px;
                            border-radius: 5px;
                            font-size: 12px;
                            z-index: 1000002;
                            border: 1px solid white;
                        }
                    `;
                    document.head.appendChild(style);
                """)

                # Set up overlay functionality with event-driven approach
                await target_page.evaluate("""
                    window.overlayActive = false;
                    
                    function createOverlay() {
                        console.log('Creating overlay...');
                        
                        if (window.overlayActive) {
                            console.log('Overlay already active');
                            return;
                        }
                        
                        const overlay = document.createElement('div');
                        overlay.className = 'element-overlay';
                        overlay.id = 'element-overlay';
                        overlay.style.position = 'fixed';
                        overlay.style.top = '0';
                        overlay.style.left = '0';
                        overlay.style.width = '100%';
                        overlay.style.height = '100%';
                        overlay.style.background = 'rgba(0, 0, 0, 0.3)';
                        overlay.style.zIndex = '999999';
                        overlay.style.pointerEvents = 'auto';
                        overlay.style.cursor = 'crosshair';
                        overlay.style.border = '2px solid red';
                        
                        document.body.appendChild(overlay);
                        console.log('Overlay element created and added to DOM');
                        
                        // Add controls panel
                        const controls = document.createElement('div');
                        controls.className = 'overlay-controls';
                        controls.innerHTML = `
                            <div><strong>XPath Capture Mode</strong></div>
                            <div>Press <kbd>ESC</kbd> to toggle overlay</div>
                        `;
                        document.body.appendChild(controls);
                        
                        window.overlayActive = true;
                        
                        // Add mouse move handler
                        overlay.addEventListener('mousemove', handleMouseMove, true);
                        
                        // Handle clicks on the overlay itself
                        overlay.addEventListener('click', handleClick, true);
                        
                        // Block other events but allow our click handler to work
                        overlay.addEventListener('mousedown', function(e) {
                            if (e.target.id === 'element-overlay') {
                                return;
                            }
                            e.preventDefault();
                            e.stopPropagation();
                            return false;
                        }, true);
                        
                        overlay.addEventListener('mouseup', function(e) {
                            if (e.target.id === 'element-overlay') {
                                return;
                            }
                            e.preventDefault();
                            e.stopPropagation();
                            return false;
                        }, true);
                        
                        // Block all other events
                        overlay.addEventListener('dblclick', preventEvent, true);
                        overlay.addEventListener('contextmenu', preventEvent, true);
                        overlay.addEventListener('keydown', preventEvent, true);
                        overlay.addEventListener('keyup', preventEvent, true);
                        overlay.addEventListener('keypress', preventEvent, true);
                        overlay.addEventListener('focus', preventEvent, true);
                        overlay.addEventListener('blur', preventEvent, true);
                        overlay.addEventListener('input', preventEvent, true);
                        overlay.addEventListener('change', preventEvent, true);
                        overlay.addEventListener('submit', preventEvent, true);
                        overlay.addEventListener('dragstart', preventEvent, true);
                        overlay.addEventListener('drop', preventEvent, true);
                        overlay.addEventListener('selectstart', preventEvent, true);
                        overlay.addEventListener('copy', preventEvent, true);
                        overlay.addEventListener('paste', preventEvent, true);
                        overlay.addEventListener('cut', preventEvent, true);
                        
                        console.log('Overlay activated - clicks allowed for XPath capture');
                    }
                    
                    function preventEvent(event) {
                        event.preventDefault();
                        event.stopPropagation();
                        event.stopImmediatePropagation();
                        return false;
                    }
                    
                    function removeOverlay() {
                        console.log('Removing overlay...');
                        const overlay = document.getElementById('element-overlay');
                        if (overlay) {
                            overlay.remove();
                            console.log('Overlay removed from DOM');
                        }
                        
                        const controls = document.querySelector('.overlay-controls');
                        if (controls) {
                            controls.remove();
                        }
                        
                        window.overlayActive = false;
                        console.log('Overlay deactivated');
                    }
                    
                    function toggleOverlay() {
                        if (window.overlayActive) {
                            removeOverlay();
                        } else {
                            createOverlay();
                        }
                    }
                    
                    function handleMouseMove(event) {
                        if (!window.overlayActive) return;
                        
                        // Temporarily hide the overlay to detect the element underneath
                        const overlay = document.getElementById('element-overlay');
                        const originalDisplay = overlay.style.display;
                        overlay.style.display = 'none';
                        
                        const element = document.elementFromPoint(event.clientX, event.clientY);
                        
                        // Restore the overlay
                        overlay.style.display = originalDisplay;
                        
                        if (!element || element.id === 'element-overlay') return;
                        
                        // Remove existing highlights
                        const existingHighlights = document.querySelectorAll('.element-highlight');
                        existingHighlights.forEach(h => h.remove());
                        
                        // Remove existing info
                        const existingInfo = document.querySelectorAll('.element-info');
                        existingInfo.forEach(i => i.remove());
                        
                        // Create highlight
                        const rect = element.getBoundingClientRect();
                        const highlight = document.createElement('div');
                        highlight.className = 'element-highlight';
                        highlight.style.left = rect.left + 'px';
                        highlight.style.top = rect.top + 'px';
                        highlight.style.width = rect.width + 'px';
                        highlight.style.height = rect.height + 'px';
                        document.body.appendChild(highlight);
                        
                        // Create info tooltip
                        const info = document.createElement('div');
                        info.className = 'element-info';
                        info.style.left = (event.clientX + 10) + 'px';
                        info.style.top = (event.clientY + 10) + 'px';
                        
                        const tagName = element.tagName.toLowerCase();
                        const id = element.id ? `#${element.id}` : '';
                        const classes = element.className ? `.${element.className.split(' ').join('.')}` : '';
                        const text = element.textContent ? element.textContent.substring(0, 30) : '';
                        
                        info.textContent = `${tagName}${id}${classes} ${text}`;
                        document.body.appendChild(info);
                    }
                    
                    function handleClick(event) {
                        if (!window.overlayActive) return;
                        
                        console.log('Click detected on overlay');
                        
                        // Temporarily hide the overlay to detect the element underneath
                        const overlay = document.getElementById('element-overlay');
                        const originalDisplay = overlay.style.display;
                        overlay.style.display = 'none';
                        
                        const element = document.elementFromPoint(event.clientX, event.clientY);
                        
                        // Restore the overlay
                        overlay.style.display = originalDisplay;
                        
                        if (!element || element.id === 'element-overlay') {
                            console.log('No valid element found at click position');
                            return;
                        }
                        
                        console.log('Element found:', element.tagName, element.id);
                        
                        // Get absolute XPath
                        const xpath = getAbsoluteXPath(element);
                        console.log('XPath generated:', xpath);
                        
                        // Store clicked element data
                        const elementData = {
                            tagName: element.tagName.toLowerCase(),
                            id: element.id,
                            className: element.className,
                            textContent: element.textContent ? element.textContent.trim() : '',
                            xpath: xpath,
                            timestamp: Date.now()
                        };
                        
                        // Send to Python via console message
                        console.log('XPath captured: ' + JSON.stringify(elementData));
                        
                        // Highlight the clicked element
                        const rect = element.getBoundingClientRect();
                        const clickHighlight = document.createElement('div');
                        clickHighlight.style.position = 'absolute';
                        clickHighlight.style.left = rect.left + 'px';
                        clickHighlight.style.top = rect.top + 'px';
                        clickHighlight.style.width = rect.width + 'px';
                        clickHighlight.style.height = rect.height + 'px';
                        clickHighlight.style.border = '3px solid #00ff00';
                        clickHighlight.style.background = 'rgba(0, 255, 0, 0.3)';
                        clickHighlight.style.pointerEvents = 'none';
                        clickHighlight.style.zIndex = '1000001';
                        document.body.appendChild(clickHighlight);
                        
                        // Remove highlight after 2 seconds
                        setTimeout(() => {
                            if (clickHighlight.parentNode) {
                                clickHighlight.parentNode.removeChild(clickHighlight);
                            }
                        }, 2000);
                        
                        // Prevent the click from reaching the underlying element
                        event.preventDefault();
                        event.stopPropagation();
                        event.stopImmediatePropagation();
                        
                        console.log('Click handled successfully');
                        return false;
                    }
                    
                    function getAbsoluteXPath(element) {
                        if (element.id) {
                            return `//*[@id="${element.id}"]`;
                        }
                        
                        if (element === document.body) {
                            return '/html/body';
                        }
                        
                        let path = '';
                        while (element && element.nodeType === Node.ELEMENT_NODE) {
                            let index = 1;
                            let sibling = element.previousSibling;
                            
                            while (sibling) {
                                if (sibling.nodeType === Node.ELEMENT_NODE && sibling.tagName === element.tagName) {
                                    index++;
                                }
                                sibling = sibling.previousSibling;
                            }
                            
                            const tagName = element.tagName.toLowerCase();
                            const pathIndex = (index > 1) ? `[${index}]` : '';
                            path = '/' + tagName + pathIndex + path;
                            
                            element = element.parentNode;
                        }
                        
                        return path;
                    }
                    
                    // Add keyboard shortcuts
                    document.addEventListener('keydown', function(event) {
                        if (event.key === 'Escape') {
                            console.log('ESC pressed - toggling overlay');
                            toggleOverlay();
                        }
                    });
                    
                    // Expose functions globally
                    window.createOverlay = createOverlay;
                    window.removeOverlay = removeOverlay;
                    window.toggleOverlay = toggleOverlay;
                """)

                # Activate the overlay
                await target_page.evaluate("window.createOverlay()")
                print("✅ Overlay activated on existing page!")
                print("\n🎮 Controls:")
                print("  • Click elements to capture XPaths")
                print("  • Press ESC to toggle overlay on/off")
                print("  • Press Ctrl+C to stop and get results")
                
                # Wait for user to stop
                try:
                    while True:
                        await asyncio.sleep(0.1)  # Check for navigation commands
                        
                        # Check for navigation commands in console
                        try:
                            # This is a simple way to check for navigation - in a real app you'd use proper event handling
                            pass
                        except Exception as e:
                            pass
                            
                except KeyboardInterrupt:
                    print("\n⏹️  Stopping...")
                    
                    if captured_elements:
                        print(f"\n📊 Total captured elements: {len(captured_elements)}")
                        print("\n📋 Element summary:")
                        for i, element in enumerate(captured_elements, 1):
                            print(f"{i:2d}. {element['tagName']:8s} - {element['xpath']}")
                            if element.get('textContent'):
                                text = element['textContent'][:30]
                                print(f"     Text: {text}")
                    else:
                        print("❌ No elements were captured.")
                        print("💡 Make sure you're clicking on elements in the browser!")
                    
                    # Remove overlay
                    try:
                        await target_page.evaluate("window.removeOverlay()")
                        print("✅ Overlay removed.")
                    except Exception as e:
                        print(f"Error removing overlay: {e}")
                    
        else:
            print(f"❌ Failed to get browser info: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Add overlay to existing browser pages (event-driven)")
    parser.add_argument("--cdp-endpoint", default="http://localhost:9222", help="CDP endpoint")
    parser.add_argument("--page-index", type=int, default=0, help="Page index to add overlay to")
    
    args = parser.parse_args()
    
    asyncio.run(add_overlay_to_existing_pages_event_driven(args.cdp_endpoint, args.page_index))


if __name__ == "__main__":
    main() 