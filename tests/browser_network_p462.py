"""Open the network study from P4.6.1 and follow its research materials."""
from urllib.parse import unquote, urlsplit


def check_page(page, base, output, device):
    response = page.goto(base + "prosperity-anchors-p461.html", wait_until="domcontentloaded")
    assert response.ok
    page.locator("#p462-entry a").click()
    page.wait_for_url("**/prosperity-network-p462.html")
    assert page.get_by_role("heading", level=1).is_visible()
    for section in ("network", "east", "outer"):
        page.locator(f'a[href="#{section}"]:visible').first.click()
        page.reload(wait_until="load")
        assert unquote(urlsplit(page.url).fragment) == section
        assert page.locator(f"#{section}").is_visible()
    page.locator('a[href="#network"]:visible').first.click()
    toggle = page.locator("#toggle-modern-river")
    layer = page.locator("svg #modern-river")
    initial = layer.evaluate("node => getComputedStyle(node).display")
    toggle.click()
    assert (layer.evaluate("node => getComputedStyle(node).display") == "none") == (initial != "none")
    toggle.click()
    assert layer.evaluate("node => getComputedStyle(node).display") == initial
    for diagram in page.locator("main img").all():
        diagram.scroll_into_view_if_needed()
        diagram.evaluate("img => img.decode()")
        assert diagram.evaluate("img => img.naturalWidth > 0")
    assert page.locator('main img[src*="network-462/"]').count() > 0
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
    for extension, magic in [("pdf", b"%PDF-"), ("zip", b"PK")]:
        link = page.locator(f'a[href$="downloads/network-462.{extension}"]').first
        assert link.is_visible()
        download = page.request.get(link.evaluate("a => a.href"))
        assert download.ok and download.body().startswith(magic)
    page.evaluate("window.scrollTo(0,0)")
    page.screenshot(path=str(output / f"p462-{device}.png"))
    page.locator("#p463-entry a").click()
    page.wait_for_url("**/prosperity-corridors-p463.html")
    for section in ("ward", "pond", "outer", "sources"):
        page.locator(f'nav a[href="#{section}"]').click()
        page.reload(wait_until="load")
        assert page.locator(f"#{section}").is_visible()
    for diagram in page.locator("main img").all():
        diagram.evaluate("img => img.decode()")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
    for extension, magic in [("pdf", b"%PDF-"), ("zip", b"PK")]:
        link = page.locator(f'a[href$="downloads/corridors-463.{extension}"]')
        download = page.request.get(link.evaluate("a => a.href"))
        assert download.ok and download.body().startswith(magic)
    page.locator('nav a[href="#ward"]').click()
    page.screenshot(path=str(output / f"p463-{device}.png"))
    page.locator("#p464-entry a").click()
    page.wait_for_url("**/prosperity-field-p464.html")
    for section in ("gate", "hongchi", "download"):
        page.locator(f'nav a[href="#{section}"]').click()
        page.reload(wait_until="load")
        assert urlsplit(page.url).fragment == section and page.locator(f"#{section}").is_visible()
    for diagram in page.locator("main img").all():
        diagram.evaluate("img => img.decode()")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
    link = page.get_by_role("link", name="下载两页 PDF 图册")
    response = page.request.get(link.evaluate("a => a.href"))
    assert response.ok and response.body().startswith(b"%PDF-")
    page.locator('nav a[href="#gate"]').click()
    page.screenshot(path=str(output / f"p464-{device}.png"))
    page.locator("#p465-entry a").click()
    page.wait_for_url("**/prosperity-gates-p465.html")
    assert page.get_by_role("heading", level=1).is_visible()
    for section in ("field", "north", "moat", "sources"):
        page.locator(f'nav a[href="#{section}"]').click()
        page.reload(wait_until="load")
        assert urlsplit(page.url).fragment == section and page.locator(f"#{section}").is_visible()
    maps = page.locator("main figure img")
    assert maps.count() == 3
    for diagram in maps.all():
        diagram.evaluate("img => img.decode()")
        assert diagram.evaluate("img => img.naturalWidth > 0")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
    download = page.get_by_role("link", name="下载三页 PDF 图册")
    result = page.request.get(download.evaluate("a => a.href"))
    assert result.ok and result.body().startswith(b"%PDF-")
    page.locator('nav a[href="#north"]').click()
    page.screenshot(path=str(output / f"p465-{device}.png"))
    page.locator("#p466-entry a").click()
    page.wait_for_url("**/prosperity-south-p466.html")
    assert page.get_by_role("heading", level=1).is_visible()
    for section in ("roads", "ditch", "waters", "sources"):
        page.locator(f'nav a[href="#{section}"]').click()
        page.reload(wait_until="load")
        assert urlsplit(page.url).fragment == section and page.locator(f"#{section}").is_visible()
    pictures = page.locator("main figure img")
    assert pictures.count() == 3
    for diagram in pictures.all():
        diagram.evaluate("img => img.decode()")
        assert diagram.evaluate("img => img.naturalWidth > 0")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
    for suffix, magic in (("south-466.pdf", b"%PDF-"), ("south-466/readings.json", b"{")):
        link = page.locator(f'a[href$="{suffix}"]')
        downloaded = page.request.get(link.evaluate("a => a.href"))
        assert downloaded.ok and downloaded.body().lstrip().startswith(magic)
    page.locator('nav a[href="#roads"]').click()
    page.screenshot(path=str(output / f"p466-{device}.png"))
    page.locator("header > a").click()
    page.wait_for_url("**/prosperity-gates-p465.html")
    page.get_by_role("link", name="返回白马寺南坊门与鸿池陂", exact=True).click()
    page.wait_for_url("**/prosperity-field-p464.html")
    page.get_by_role("link", name="返回外郭九道、白马寺与鸿池陂", exact=True).click()
    page.wait_for_url("**/prosperity-corridors-p463.html")
    page.locator('header a').click()
    page.wait_for_url("**/prosperity-network-p462.html")
    page.locator('a[href$="prosperity-anchors-p461.html"]').first.click()
    page.wait_for_url("**/prosperity-anchors-p461.html")
    assert page.locator("#p462-entry").is_visible()
