"""Measure an atlas only after its current document has finished loading.

This waits for a browser lifecycle event, not for a failing layout to become
acceptable. Each caller keeps its existing width tolerance and assertions.
"""


def assert_loaded_viewport(page, *, tolerance, report=None):
    # Text/count assertions alone can pass before CSS and deferred scripts load.
    page.wait_for_load_state("load", timeout=30_000)
    layout = page.evaluate("""() => {
        const map = document.querySelector('#map-scroll, .map-scroll');
        return {
            ready_state: document.readyState,
            document_width: document.documentElement.scrollWidth,
            client_width: document.documentElement.clientWidth,
            inner_width: innerWidth,
            body_margin: getComputedStyle(document.body).margin,
            map_overflow_x: map ? getComputedStyle(map).overflowX : null
        };
    }""")
    layout["tolerance"] = tolerance
    if layout["document_width"] > layout["inner_width"] + tolerance:
        layout["overflow_elements"] = page.evaluate("""tolerance => Array.from(document.querySelectorAll(
            'body, header, main, footer, .wrap, figure, .canvas, .map-scroll, #map-scroll, #road-map, #all-road-map, .reading, .filter, .filters, .road summary, .segment summary, .supplements, .audit, .downloads'
        )).map(el => {
            const box = el.getBoundingClientRect();
            return {tag: el.tagName, id: el.id, class_name: el.getAttribute('class'),
                left: box.left, right: box.right, width: box.width,
                overflow_x: getComputedStyle(el).overflowX};
        }).filter(box => box.left < -tolerance || box.right > innerWidth + tolerance).slice(0, 20)""", tolerance)
    evidence = dict(url=page.url, **layout)
    if report is not None:
        report.setdefault("layout_checks", []).append(evidence)
    assert layout["document_width"] <= layout["inner_width"] + tolerance, evidence
    return layout
