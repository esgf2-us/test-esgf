import { check } from 'k6';
import { browser } from 'k6/experimental/browser';

export const options = {
    scenarios: {
        ui: {
            executor: 'shared-iterations',
            options:{
                browser: {
                    type: 'chromium'
                }
            }
        }
    }
}

export default async function () {
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

        /* If the copy search button is clickable, the query is finished */
        await page.locator("//button/span[text()='Copy Search']").click();

        check(page, {
            title: page.locator('title').textContent() == 'ESGF MetaGrid',
        });

    } finally {
        page.close();
    }
}
