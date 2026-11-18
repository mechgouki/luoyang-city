"""Exercise the published P4.6.1 entry, reading anchors and source illustrations."""
from urllib.parse import unquote, urlsplit


def check_page(page, base, output, device):
    previous = base + "prosperity-hydro-roads.html"
    response = page.goto(previous, wait_until="domcontentloaded")
    assert response.ok
    page.locator("#p461-entry a").click()
    page.wait_for_url("**/prosperity-anchors-p461.html")
    assert page.locator("h1").is_visible()
    link = page.locator('a[href^="#"]:not([href="#"]):visible').first
    fragment = link.get_attribute("href")
    link.click()
    assert page.evaluate("(anchor) => !!document.getElementById(decodeURIComponent(anchor.slice(1)))", fragment)
    page.reload(wait_until="load")
    assert unquote(urlsplit(page.url).fragment) == unquote(fragment[1:])
    for img in page.locator("main img").all():
        img.scroll_into_view_if_needed()
        img.evaluate("img => img.decode()")
        assert img.evaluate("img => img.naturalWidth > 0")
    assert page.locator("main img").count() > 0
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
    page.evaluate("window.scrollTo(0,0)")
    page.screenshot(path=str(output / f"p461-{device}.png"))
    assert page.locator('a[href$="downloads/anchor-461.zip"]').count() >= 1
    assert page.locator('a[href$="downloads/anchor-461.pdf"]').count() >= 1
    page.locator('a[href$="prosperity-hydro-roads.html"]').first.click()
    page.wait_for_url("**/prosperity-hydro-roads.html")
    assert page.locator("#p461-entry").is_visible()
