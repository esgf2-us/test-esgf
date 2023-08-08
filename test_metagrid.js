import { check } from 'k6';
import { chromium } from 'k6/experimental/browser';

export default async function () {
    const browser = chromium.launch({ headless: false });
    const page = browser.newPage();

    try {
        //await page.goto('https://aims2.llnl.gov/search');
        await page.goto('https://esgf-node.ornl.gov/search');

        /* Dismiss welcome windows and select CMIP6 project */
        page.locator("//button/span[text()='Close']").click();
        page.locator("//button[@title='Skip']").click();
        page.locator("//button/span[@class='anticon anticon-select']").click();

        /* Wait for default query and then expand all tabs */
        await page.locator("//button/span[text()='Expand All']").click();

        /* Define a facet search and plug into the html */
        const facets = {
            "source_id": "CESM2",
            "experiment_id": "historical",
            "variant_label": "r1i1p1f1",
            "variable_id": "gpp",
        };
        for (const [key, value] of Object.entries(facets)) {
            const facet = page.locator(`#${key}`);
            facet.type(value);
            facet.press("Enter");
            facet.press("Escape");
        }

        /* Wait until the results show up for timing */
        await page.locator("//tr[@class='ant-table-row ant-table-row-level-0']"); // <-- this isn't waiting

        check(page, {
            header: page.locator('title').textContent() == 'ESGF MetaGrid',
        });

    } finally {
        page.close();
        browser.close();
    }
}
