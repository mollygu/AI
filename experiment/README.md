# Experiment

## Start custom codegen with the ability to take snapshots and call the devtest mcp tools to get the test detail and save to testplan file.
    ~/start_codegen.sh $templateid &

## Start the monitor to generate modified recorded scripts
    cd  /Users/juagu/Documents/work_2025/ngc-ui-test
    python monitor_snapshots.py $templateid
    
## Sample
### Test detail will save to a testplan_{casenumber}.md
Example:
```
Template ID: 3574605
Title: [Guest][UI] Can't view container scanning results
Test Steps:
  ......
  
  Expected result
  ......
```
### Recorded script
Example, {casenumber}_with_snapshots.py:
```
    import re
    from playwright.sync_api import Page, expect


    def test_example(page: Page) -> None:
        page.goto("https://catalog.stg.ngc.nvidia.com/?filters=&orderBy=weightPopularDESC&query=&page=&pageSize=")
        page.get_by_role("button", name="Accept All").click()
        # - 02-click-internal_role_button_name__Acc...-2025-04-11T06-41-31-734Z.aria.txt
        # - 02-click-internal_role_button_name__Acc...-2025-04-11T06-41-31-734Z.html
        # - 02-click-internal_role_button_name__Acc...-2025-04-11T06-41-31-734Z.png

        page.get_by_test_id("kui-vertical-nav-accordion-root").get_by_role("link", name="Containers").click()
        # - 03-click-internal_testid__data_testid__...-2025-04-11T06-41-35-265Z.aria.txt
        # - 03-click-internal_testid__data_testid__...-2025-04-11T06-41-35-265Z.html
        # - 03-click-internal_testid__data_testid__...-2025-04-11T06-41-35-265Z.png

        page.goto("https://catalog.stg.ngc.nvidia.com/?filters=&orderBy=weightPopularDESC&query=&page=&pageSize=")
        # - 04-navigate-2025-04-11T06-42-09-823Z.aria.txt
        # - 04-navigate-2025-04-11T06-42-09-823Z.html
        # - 04-navigate-2025-04-11T06-42-09-823Z.png

        page.get_by_test_id("kui-vertical-nav-accordion-root").get_by_role("link", name="Containers").click()
        # - 05-click-internal_testid__data_testid__...-2025-04-11T06-42-15-791Z.aria.txt
        # - 05-click-internal_testid__data_testid__...-2025-04-11T06-42-15-791Z.html
        # - 05-click-internal_testid__data_testid__...-2025-04-11T06-42-15-791Z.png

        page.get_by_role("link", name="Logo for busybox busybox for").click()
        # - 06-click-internal_role_link_name__Logo_...-2025-04-11T06-42-21-430Z.aria.txt
        # - 06-click-internal_role_link_name__Logo_...-2025-04-11T06-42-21-430Z.html
        # - 06-click-internal_role_link_name__Logo_...-2025-04-11T06-42-21-430Z.png

        page.get_by_role("tab", name="Security Scanning").click()
        # - 07-navigate-2025-04-11T06-42-27-513Z.aria.txt
        # - 07-navigate-2025-04-11T06-42-27-513Z.html
        # - 07-navigate-2025-04-11T06-42-27-513Z.png

        expect(page.get_by_test_id("kui-status-message-header")).to_be_visible()

```
