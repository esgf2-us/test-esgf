import time

import numpy as np
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

MAX_WAIT_TIME = 60


def metagrid_search(
    site: str,
    facets: dict[str],
) -> float:
    """Return the time in seconds required to perform a Metagrid search.

    Note that the time reported starts just before typing the search facets and ends
    once a row of results has been returned.
    """
    driver = webdriver.Firefox()
    driver.get(site)
    assert "ESGF MetaGrid" in driver.title

    # Dismiss welcome windows,
    elem = driver.find_element(By.XPATH, "//button/span[text()='Close']")
    elem.click()
    elem = driver.find_element(By.XPATH, "//button[@title='Skip']")
    elem.click()

    # Select the CMIP6 project
    elem = driver.find_element(
        By.XPATH, '//button/span[@class="anticon anticon-select"]'
    )
    elem.click()

    # Click on "Expand All" to expose all facets, won't be available until the query
    # returns from the previous action.
    elem = WebDriverWait(driver, MAX_WAIT_TIME).until(
        expected_conditions.presence_of_element_located(
            (By.XPATH, "//button/span[text()='Expand All']")
        )
    )
    elem.click()

    # Loop through the facets and insert the text values into Metagrid
    for key, value in facets.items():
        elem = driver.find_element(By.ID, key)
        elem.send_keys(value)
        elem.send_keys(Keys.ENTER)
        elem.send_keys(Keys.ESCAPE)

    search_time = time.perf_counter()
    WebDriverWait(driver, MAX_WAIT_TIME).until(
        expected_conditions.presence_of_element_located(
            (By.XPATH, "//tr[@class='ant-table-row ant-table-row-level-0']")
        )
    )
    driver.close()
    search_time = time.perf_counter() - search_time
    return search_time


def benchmark_metagrid(
    site: str, facets: dict, typical_mean: float, typical_std: float, repeat: int = 3
):
    times = []
    for i in range(repeat):
        times.append(metagrid_search(site, facets))
    times = np.array(times)
    print(f"{site}  {times.mean():.2f} ± {times.std():.2f} [s]")
    if np.abs(times.mean() - typical_mean) / typical_std > 1:
        raise ValueError(
            f"Search times have significantly changed for {site}, {typical_mean} ± {typical_std} [s] --> {times.mean():.2f} ± {times.std():.2f} [s]"
        )


@pytest.mark.ornl
@pytest.mark.performance
def test_ornl_metagrid_speed():
    facets = {
        "source_id": "CESM2",
        "experiment_id": "historical",
        "variant_label": "r1i1p1f1",
        "variable_id": "gpp",
    }
    benchmark_metagrid("https://esgf-node.ornl.gov/search", facets, 16.35, 0.14)


@pytest.mark.llnl
@pytest.mark.performance
def test_llnl_metagrid_speed():
    facets = {
        "source_id": "CESM2",
        "experiment_id": "historical",
        "variant_label": "r1i1p1f1",
        "variable_id": "gpp",
    }
    benchmark_metagrid("https://aims2.llnl.gov/search", facets, 2.35, 0.08)
