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
                
                # Store the last page where overlay was added
                last_overlay_page = None
                
                # Set up console message listener
                async def handle_console(msg):
                    if msg.type == 'log' and 'XPath captured:' in msg.text:
                        try:
                            # Extract XPath data from console message
                            xpath_data = msg.text.split('XPath captured: ')[1]
                            element_data = json.loads(xpath_data)
                            captured_elements.append(element_data)
                            print(f"\n🎯 Captured element:")
                            print(f"  Tag: {element_data['tagName']}")
                            print(f"  Absolute XPath: {element_data['xpath']}")
                            
                            own_unique_xpath = element_data.get('ownUniqueXPath', 'N/A')
                            if own_unique_xpath == "no unique attribute":
                                print(f"  Own Unique XPath: ❌ {own_unique_xpath}")
                            elif isinstance(own_unique_xpath, list):
                                print(f"  Own Unique XPaths: ✅ Found {len(own_unique_xpath)} options:")
                                for i, xpath_info in enumerate(own_unique_xpath, 1):
                                    print(f"    {i}. {xpath_info['type']}: {xpath_info['xpath']}")
                            else:
                                print(f"  Own Unique XPath: ✅ {own_unique_xpath}")
                                
                            # Display HTML (truncated if too long)
                            html = element_data.get('html', '')
                            if html:
                                if len(html) > 200:
                                    print(f"  HTML: {html[:200]}...")
                                else:
                                    print(f"  HTML: {html}")
                        except Exception as e:
                            print(f"Error parsing XPath data: {e}")
                    elif msg.type == 'log' and 'Trying XPath:' in msg.text:
                        # Display XPath trying logs in terminal
                        print(f"  🔍 {msg.text}")
                    elif msg.type == 'log' and '=== getOwnUniqueXPath ===' in msg.text:
                        # Display when XPath generation starts
                        print(f"\n🔍 {msg.text}")
                    elif msg.type == 'log' and '=== getAbsoluteXPath ===' in msg.text:
                        # Display when absolute XPath generation starts
                        print(f"\n🔍 {msg.text}")
                    elif msg.type == 'log' and 'Element:' in msg.text:
                        # Display element info
                        print(f"  📄 {msg.text}")
                    elif msg.type == 'log' and 'Using ' in msg.text and ':' in msg.text:
                        # Display which attribute was used
                        print(f"  ✅ {msg.text}")
                    elif msg.type == 'log' and 'Found unique XPaths:' in msg.text:
                        # Display how many unique XPaths were found
                        count = msg.text.split('Found unique XPaths: ')[1]
                        print(f"  🎯 {msg.text}")
                    elif msg.type == 'log' and 'Own Unique XPath generated:' in msg.text:
                        # Display the final generated XPath(s)
                        xpath_data = msg.text.split('Own Unique XPath generated: ')[1]
                        print(f"  🎯 Generated: {xpath_data}")
                    elif msg.type == 'log' and 'No unique attributes found' in msg.text:
                        # Display when no unique attributes are found
                        print(f"  ❌ {msg.text}")
                
                # Listen for console messages
                target_page.on('console', handle_console)
                
                # Listen for page navigation events
                async def handle_navigation():
                    nonlocal last_overlay_page
                    
                    # Get the current URL after navigation
                    current_url = target_page.url
                    
                    # print(f"\n🔄 Navigation detected: {current_url}")
                    
                    # Check if we've already added overlay to this page
                    if last_overlay_page == current_url:
                        # print("💡 Overlay already exists on this page, skipping re-injection")
                        return
                    
                    # Check if it's a different domain or just URL parameters change
                    from urllib.parse import urlparse
                    
                    if last_overlay_page:
                        last_parsed = urlparse(last_overlay_page)
                        current_parsed = urlparse(current_url)
                        
                        # If same domain, it's the same application - overlay should persist
                        if last_parsed.netloc == current_parsed.netloc:
                            # print("💡 Same domain - overlay should persist")
                            return
                    
                    print("🔄 New domain/page detected - re-injecting overlay...")
                    await inject_overlay_script(target_page)
                    last_overlay_page = current_url
                    print("✅ Overlay re-injected after navigation")
                
                target_page.on('framenavigated', handle_navigation)
                
                async def inject_overlay_script(target_page):
                    """
                    Inject the overlay script into the target page.
                    
                    Args:
                        target_page: The page to inject the overlay into
                    """
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
                        // Clean up any existing overlay state first
                        if (window.overlayActive) {
                            console.log('Cleaning up existing overlay state...');
                            const existingOverlay = document.getElementById('element-overlay');
                            if (existingOverlay) {
                                existingOverlay.remove();
                            }
                            const existingControls = document.querySelector('.overlay-controls');
                            if (existingControls) {
                                existingControls.remove();
                            }
                            const existingHighlights = document.querySelectorAll('.element-highlight');
                            existingHighlights.forEach(h => h.remove());
                            const existingInfo = document.querySelectorAll('.element-info');
                            existingInfo.forEach(i => i.remove());
                            const existingStyles = document.querySelector('style');
                            if (existingStyles && existingStyles.textContent.includes('.element-overlay')) {
                                existingStyles.remove();
                            }
                            window.overlayActive = false;
                        }
                        
                        // Remove any existing keyboard event listeners
                        if (window.overlayKeyHandler) {
                            document.removeEventListener('keydown', window.overlayKeyHandler);
                            console.log('Removed existing keyboard event listener');
                        }
                        
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
                                <div>Press <kbd>R</kbd> to reset completely</div>
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
                        
                        function resetOverlay() {
                            console.log('Resetting overlay completely...');
                            
                            // Remove overlay
                            removeOverlay();
                            
                            // Remove all highlights and info tooltips
                            const highlights = document.querySelectorAll('.element-highlight');
                            highlights.forEach(h => h.remove());
                            console.log('Removed highlights');
                            
                            const infoTooltips = document.querySelectorAll('.element-info');
                            infoTooltips.forEach(i => i.remove());
                            console.log('Removed info tooltips');
                            
                            // Remove any click highlights (green borders)
                            const clickHighlights = document.querySelectorAll('[style*="border: 3px solid #00ff00"]');
                            clickHighlights.forEach(h => h.remove());
                            console.log('Removed click highlights');
                            
                            // Remove the overlay styles
                            const overlayStyles = document.querySelector('style');
                            if (overlayStyles && overlayStyles.textContent.includes('.element-overlay')) {
                                overlayStyles.remove();
                                console.log('Removed overlay styles');
                            }
                            
                            // Reset global state
                            window.overlayActive = false;
                            window.createOverlay = null;
                            window.removeOverlay = null;
                            window.toggleOverlay = null;
                            window.resetOverlay = null;
                            
                            console.log('Overlay completely reset - all event listeners and DOM elements removed');
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
                            
                            // Get readable XPath
                            const ownUniqueXPath = getOwnUniqueXPath(element);
                            console.log('Own Unique XPath generated:', ownUniqueXPath);
                            
                            // Log element details for debugging
                            console.log('Element details:', {
                                tagName: element.tagName,
                                id: element.id,
                                className: element.className,
                                textContent: element.textContent ? element.textContent.trim() : '',
                                html: element.outerHTML
                            });
                            
                            // Store clicked element data
                            const elementData = {
                                tagName: element.tagName.toLowerCase(),
                                id: element.id,
                                className: element.className,
                                textContent: element.textContent ? element.textContent.trim() : '',
                                xpath: xpath,
                                ownUniqueXPath: ownUniqueXPath,
                                html: element.outerHTML,
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
                            console.log('=== getAbsoluteXPath ===');
                            
                            if (element.id) {
                                const xpath = `//*[@id="${element.id}"]`;
                                if (isXPathUnique(xpath)) {
                                    return xpath;
                                }
                            }
                            
                            if (element === document.body) {
                                const xpath = '/html/body';
                                if (isXPathUnique(xpath)) {
                                    return xpath;
                                }
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
                            
                            // Verify the generated absolute XPath is unique
                            if (isXPathUnique(path)) {
                                return path;
                            } else {
                                console.log('Generated absolute XPath is not unique, this should not happen:', path);
                                // Fallback: add position() to make it unique
                                return path + '[1]';
                            }
                        }
                        
                        function isXPathUnique(xpath) {
                            try {
                                const xpathElements = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                                const count = xpathElements.snapshotLength;
                                
                                // Track logged XPaths to avoid duplicates
                                if (!window.loggedXPaths) {
                                    window.loggedXPaths = new Set();
                                }
                                
                                if (!window.loggedXPaths.has(xpath)) {
                                    console.log(`Trying XPath: "${xpath}", count: ${count}`);
                                    window.loggedXPaths.add(xpath);
                                }
                                
                                return count === 1;
                            } catch (error) {
                                console.log(`Error evaluating XPath "${xpath}":`, error);
                                return false;
                            }
                        }
                        
                        function getOwnUniqueXPath(element) {
                            console.log('=== getOwnUniqueXPath ===');
                            console.log('Element:', element.tagName, element.id, element.className);
                            
                            // Clear logged XPaths for this element
                            window.loggedXPaths = new Set();
                            
                            const uniqueXPaths = [];
                            
                            // 1. If element has an ID, use it (shortest and most reliable)
                            if (element.id) {
                                const xpath = `//*[@id="${element.id}"]`;
                                if (isXPathUnique(xpath)) {
                                    console.log('Using ID:', element.id);
                                    uniqueXPaths.push({ type: 'ID', xpath: xpath, value: element.id });
                                }
                            }
                            
                            // 2. If element has unique exact text content, use it (very reliable)
                            if (element.textContent && element.textContent.trim()) {
                                const text = element.textContent.trim();
                                
                                if (text.length > 2 && text.length < 100) { // Reasonable text length
                                    // Escape quotes for XPath
                                    const escapedText = text.replace(/"/g, '\\"').replace(/'/g, "\\'");
                                    
                                    // First try exact text match
                                    const exactXpath = `//${element.tagName.toLowerCase()}[text()="${escapedText}"]`;
                                    if (isXPathUnique(exactXpath)) {
                                        console.log('Using exact textContent match:', text);
                                        uniqueXPaths.push({ type: 'Exact TextContent', xpath: exactXpath, value: text });
                                    } else {
                                        // If exact match fails, try contains
                                        const containsXpath = `//${element.tagName.toLowerCase()}[contains(text(),"${escapedText}")]`;
                                        if (isXPathUnique(containsXpath)) {
                                            console.log('Using contains textContent match:', text);
                                            uniqueXPaths.push({ type: 'Contains TextContent', xpath: containsXpath, value: text });
                                        }
                                    }
                                }
                            }
                            
                            // 3. If element has unique innerText content, use it (more normalized)
                            if (element.innerText && element.innerText.trim()) {
                                const innerText = element.innerText.trim();
                                
                                // Check if innerText is different from textContent
                                const textContent = element.textContent ? element.textContent.trim() : '';
                                if (innerText === textContent) {
                                    console.log('innerText is same as textContent, skipping to avoid duplicate');
                                } else {
                                    if (innerText.length > 2 && innerText.length < 100) { // Reasonable text length
                                        // Escape quotes for XPath
                                        const escapedInnerText = innerText.replace(/"/g, '\\"').replace(/'/g, "\\'");
                                        
                                        // First try exact text match
                                        const exactXpath = `//${element.tagName.toLowerCase()}[text()="${escapedInnerText}"]`;
                                        if (isXPathUnique(exactXpath)) {
                                            console.log('Using exact innerText match:', innerText);
                                            uniqueXPaths.push({ type: 'Exact InnerText', xpath: exactXpath, value: innerText });
                                        } else {
                                            // If exact match fails, try contains
                                            const containsXpath = `//${element.tagName.toLowerCase()}[contains(text(),"${escapedInnerText}")]`;
                                            if (isXPathUnique(containsXpath)) {
                                                console.log('Using contains innerText match:', innerText);
                                                uniqueXPaths.push({ type: 'Contains InnerText', xpath: containsXpath, value: innerText });
                                            }
                                        }
                                    }
                                }
                            }
                            
                            // 4. If element has data-icon-name, use it (great for icons)
                            if (element.hasAttribute('data-icon-name')) {
                                const iconName = element.getAttribute('data-icon-name');
                                const xpath = `//${element.tagName.toLowerCase()}[@data-icon-name="${iconName}"]`;
                                if (isXPathUnique(xpath)) {
                                    console.log('Using data-icon-name:', iconName);
                                    uniqueXPaths.push({ type: 'data-icon-name', xpath: xpath, value: iconName });
                                }
                            }
                            
                            // 5. If element has data-testid, use it (specifically designed for testing)
                            if (element.hasAttribute('data-testid')) {
                                const testId = element.getAttribute('data-testid');
                                const xpath = `//${element.tagName.toLowerCase()}[@data-testid="${testId}"]`;
                                if (isXPathUnique(xpath)) {
                                    console.log('Using data-testid:', testId);
                                    uniqueXPaths.push({ type: 'data-testid', xpath: xpath, value: testId });
                                }
                            }
                            
                            // 6. Check for other unique data attributes
                            const dataAttrs = ['data-id', 'data-name', 'data-value', 'data-label', 'data-cy', 'data-qa'];
                            for (let attr of dataAttrs) {
                                if (element.hasAttribute(attr)) {
                                    const value = element.getAttribute(attr);
                                    const xpath = `//${element.tagName.toLowerCase()}[@${attr}="${value}"]`;
                                    if (isXPathUnique(xpath)) {
                                        console.log('Using data attribute:', attr, value);
                                        uniqueXPaths.push({ type: attr, xpath: xpath, value: value });
                                    }
                                }
                            }
                            
                            // 7. If element has a unique aria-label, use it
                            if (element.hasAttribute('aria-label')) {
                                const ariaLabel = element.getAttribute('aria-label');
                                const xpath = `//${element.tagName.toLowerCase()}[@aria-label="${ariaLabel}"]`;
                                if (isXPathUnique(xpath)) {
                                    console.log('Using aria-label:', ariaLabel);
                                    uniqueXPaths.push({ type: 'aria-label', xpath: xpath, value: ariaLabel });
                                }
                            }
                            
                            // 8. If element has a unique title, use it
                            if (element.hasAttribute('title')) {
                                const title = element.getAttribute('title');
                                const xpath = `//${element.tagName.toLowerCase()}[@title="${title}"]`;
                                if (isXPathUnique(xpath)) {
                                    console.log('Using title:', title);
                                    uniqueXPaths.push({ type: 'title', xpath: xpath, value: title });
                                }
                            }
                            
                            // 9. If element has a unique name attribute, use it
                            if (element.hasAttribute('name')) {
                                const name = element.getAttribute('name');
                                const xpath = `//${element.tagName.toLowerCase()}[@name="${name}"]`;
                                if (isXPathUnique(xpath)) {
                                    console.log('Using name:', name);
                                    uniqueXPaths.push({ type: 'name', xpath: xpath, value: name });
                                }
                            }
                            
                            // 10. If element has a unique placeholder, use it
                            if (element.hasAttribute('placeholder')) {
                                const placeholder = element.getAttribute('placeholder');
                                const xpath = `//${element.tagName.toLowerCase()}[@placeholder="${placeholder}"]`;
                                if (isXPathUnique(xpath)) {
                                    console.log('Using placeholder:', placeholder);
                                    uniqueXPaths.push({ type: 'placeholder', xpath: xpath, value: placeholder });
                                }
                            }
                            
                            // 11. If element has a unique value attribute, use it
                            if (element.hasAttribute('value')) {
                                const value = element.getAttribute('value');
                                // Skip empty values as they're not meaningful
                                if (value && value.trim() !== '') {
                                    const xpath = `//${element.tagName.toLowerCase()}[@value="${value}"]`;
                                    if (isXPathUnique(xpath)) {
                                        console.log('Using value:', value);
                                        uniqueXPaths.push({ type: 'value', xpath: xpath, value: value });
                                    }
                                }
                            }
                            
                            // 12. If element has a unique type attribute, use it
                            if (element.hasAttribute('type')) {
                                const type = element.getAttribute('type');
                                const xpath = `//${element.tagName.toLowerCase()}[@type="${type}"]`;
                                if (isXPathUnique(xpath)) {
                                    console.log('Using type:', type);
                                    uniqueXPaths.push({ type: 'type', xpath: xpath, value: type });
                                }
                            }
                            
                            // 13. If element has a unique href attribute, use it
                            if (element.hasAttribute('href')) {
                                const href = element.getAttribute('href');
                                const xpath = `//${element.tagName.toLowerCase()}[@href="${href}"]`;
                                if (isXPathUnique(xpath)) {
                                    console.log('Using href:', href);
                                    uniqueXPaths.push({ type: 'href', xpath: xpath, value: href });
                                }
                            }
                            
                            // 14. If element has a unique src attribute, use it
                            if (element.hasAttribute('src')) {
                                const src = element.getAttribute('src');
                                const xpath = `//${element.tagName.toLowerCase()}[@src="${src}"]`;
                                if (isXPathUnique(xpath)) {
                                    console.log('Using src:', src);
                                    uniqueXPaths.push({ type: 'src', xpath: xpath, value: src });
                                }
                            }
                            
                            // 15. If element has a unique alt attribute, use it
                            if (element.hasAttribute('alt')) {
                                const alt = element.getAttribute('alt');
                                const xpath = `//${element.tagName.toLowerCase()}[@alt="${alt}"]`;
                                if (isXPathUnique(xpath)) {
                                    console.log('Using alt:', alt);
                                    uniqueXPaths.push({ type: 'alt', xpath: xpath, value: alt });
                                }
                            }
                            
                            // 16. If element has a unique role attribute, use it
                            if (element.hasAttribute('role')) {
                                const role = element.getAttribute('role');
                                const xpath = `//${element.tagName.toLowerCase()}[@role="${role}"]`;
                                if (isXPathUnique(xpath)) {
                                    console.log('Using role:', role);
                                    uniqueXPaths.push({ type: 'role', xpath: xpath, value: role });
                                }
                            }
                            
                            if (uniqueXPaths.length > 0) {
                                console.log('Found unique XPaths:', uniqueXPaths.length);
                                return uniqueXPaths;
                            } else {
                                console.log('No unique attributes found');
                                return "no unique attribute";
                            }
                        }
                        
                        // Expose functions globally
                        window.createOverlay = createOverlay;
                        window.removeOverlay = removeOverlay;
                        window.toggleOverlay = toggleOverlay;
                        window.resetOverlay = resetOverlay;
                        
                        console.log('All overlay functions defined and exposed to window object');
                        
                        // Add keyboard shortcuts AFTER functions are defined
                        window.overlayKeyHandler = function(event) {
                            if (event.key === 'Escape') {
                                console.log('ESC pressed - toggling overlay');
                                toggleOverlay();
                            } else if (event.key === 'r' || event.key === 'R') {
                                console.log('R pressed - resetting overlay completely');
                                resetOverlay();
                            }
                        };
                        
                        document.addEventListener('keydown', window.overlayKeyHandler);
                        console.log('Keyboard event listener added');
                    """)

                    # Activate the overlay
                    try:
                        # Add a small delay to ensure functions are properly defined
                        await asyncio.sleep(0.1)
                        
                        # Check if function exists before calling
                        function_exists = await target_page.evaluate("typeof window.createOverlay === 'function'")
                        if function_exists:
                            await target_page.evaluate("window.createOverlay()")
                            print("✅ Overlay activated!")
                        else:
                            print("❌ Error: createOverlay function not found")
                            return
                            
                    except Exception as e:
                        print(f"❌ Error activating overlay: {e}")
                        return
                
                # Add overlay CSS and JavaScript
                await inject_overlay_script(target_page)
                
                # Update the last overlay page
                last_overlay_page = target_page.url
                    
                print("\n🎮 Controls:")
                print("  • Click elements to capture XPaths")
                print("  • Press ESC to toggle overlay on/off")
                print("  • Press R to reset completely (remove all)")
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
                            print(f"{i:2d}. {element['tagName']:8s}")
                            print(f"     Absolute: {element['xpath']}")
                            
                            own_unique_xpath = element.get('ownUniqueXPath', 'N/A')
                            if own_unique_xpath == "no unique attribute":
                                print(f"     Own Unique: ❌ {own_unique_xpath}")
                            elif isinstance(own_unique_xpath, list):
                                print(f"     Own Unique XPaths: ✅ Found {len(own_unique_xpath)} options:")
                                for j, xpath_info in enumerate(own_unique_xpath, 1):
                                    print(f"        {j}. {xpath_info['type']}: {xpath_info['xpath']}")
                            else:
                                print(f"     Own Unique XPath: ✅ {own_unique_xpath}")
                                
                            if element.get('textContent'):
                                text = element['textContent'][:30]
                                print(f"     Text: {text}")
                            print()
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