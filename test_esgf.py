import re
import timeit
from functools import partial

import numpy as np
import pytest
import requests
from netCDF4 import Dataset
from pyesgf.search import SearchConnection

EXPECTED_FILES = 40000000


def get_page_links(page_url):
    """Get all the urls on this page, but ignore those which link to catalogs or ipython
    notebooks. If the request status code is not 200, will throw an error."""
    resp = requests.get(page_url)
    if resp.status_code != requests.codes.ok:
        raise ValueError("Failed to load catalog page")
    root = page_url[: page_url.index("/", 8)]
    urls = re.findall(r'a href=[\'"]?([^\'" >]+)', str(resp.content))
    urls = [
        root + url
        for url in urls
        if (not url.endswith(".ipynb") and not url.endswith("catalog.html"))
    ]
    return urls


def check_search(esg_search: str):
    """Given the connection for the search, use pyesgf to check search results."""
    conn = SearchConnection(esg_search, distrib=False, timeout=600)
    ctx = conn.new_context(
        facets=[
            "project",
            "experiment_id",
            "source_id",
            "member_id",
            "grid_label",
            "frequency",
            "variable_id",
        ],
        project="CMIP6",
        experiment_id="historical",
        source_id=["CESM2", "NorESM2-LM"],
        member_id="r1i1p1f1",
        grid_label="gn",
        frequency=["mon"],
        variable_id=["gpp"],
        latest=True,
    )
    if ctx.hit_count == 0:
        raise ValueError(f"The {esg_search} connection returns no results.")
    results = ctx.search()
    return results


def check_file_core(core):
    file_url = f"https://{core}/esg-search/search?type=File&distrib=false&limit=0&format=application%2fsolr%2bjson"
    resp = requests.get(file_url)

    numfound = resp.json()["response"]["numFound"]
    if numfound < EXPECTED_FILES:
        raise ValueError(
            f"At {core}: {numfound} files found, below the {EXPECTED_FILES} threshold."
        )


def benchmark_search(core, typical_mean, typical_std, repeat=10):
    times = np.array(
        timeit.repeat(partial(check_search, core), number=1, repeat=repeat)
    )
    print(f"{core}  {times.mean():.2f} ± {times.std():.2f} [s]")
    if np.abs(times.mean() - typical_mean) / typical_std > 1:
        raise ValueError(
            f"Search times have significantly changed for {core}, {typical_mean} ± {typical_std} [s] --> {times.mean():.2f} ± {times.std():.2f} [s]"
        )


@pytest.mark.ornl
def test_ornl_https_download_links():
    urls = get_page_links(
        (
            "https://esgf-node.ornl.gov/thredds/catalog/css03_data/CMIP6/"
            "CMIP/NCAR/CESM2/historical/r1i1p1f1/fx/areacella/gn/v20190308/catalog.html?dataset="
            "css03_data/CMIP6/CMIP/NCAR/CESM2/historical/r1i1p1f1/fx/areacella/gn/v20190308/"
            "areacella_fx_CESM2_historical_r1i1p1f1_gn.nc"
        )
    )
    for url in urls:
        if "dodsC" in url:
            continue
        resp = requests.get(url)
        if resp.status_code != requests.codes.ok:
            raise ValueError(
                f"ORNL HTTPServer link returning invalid response: {resp.status_code}"
            )


@pytest.mark.ornl
def test_ornl_opendap_download_links():
    urls = get_page_links(
        (
            "https://esgf-node.ornl.gov/thredds/catalog/"
            "css03_data/CMIP6/CMIP/NCAR/CESM2/historical/r1i1p1f1/fx/areacella/gn/v20190308/catalog.html?dataset="
            "css03_data/CMIP6/CMIP/NCAR/CESM2/historical/r1i1p1f1/fx/areacella/gn/v20190308/areacella_fx_CESM2_historical_r1i1p1f1_gn.nc"
        )
    )
    for url in urls:
        if "dodsC" not in url:
            continue
        url = url.replace(".html", "")
        # just open and read the data, this could be smarter
        with Dataset(url) as dset:
            for var in dset.variables:
                _ = dset[var][...]


@pytest.mark.llnl
def test_llnl_https_download_links():
    urls = get_page_links(
        (
            "https://nimbus6.llnl.gov/thredds/catalog/"
            "css03_data/CMIP6/CMIP/NCAR/CESM2/historical/r1i1p1f1/fx/areacella/gn/v20190308/catalog.html?dataset="
            "css03_data/CMIP6/CMIP/NCAR/CESM2/historical/r1i1p1f1/fx/areacella/gn/v20190308/areacella_fx_CESM2_historical_r1i1p1f1_gn.nc"
        )
    )
    for url in urls:
        if "dodsC" in url:
            continue
        resp = requests.get(url)
        if resp.status_code != requests.codes.ok:
            raise ValueError(
                f"LLNL HTTPServer link returning invalid response: {resp.status_code}"
            )


@pytest.mark.ornl
def test_ornl_search():
    results = check_search("https://esgf-node.ornl.gov/esg-search/")
    for dsr in results:
        links = [
            fr.opendap_url
            for fr in dsr.file_context().search()
            if fr.opendap_url is not None
        ]
        if len(links) != dsr.number_of_files:
            raise ValueError(
                f"{dsr.dataset_id} number of files ({len(links)}) not equal to the results number ({dsr.number_of_links})"
            )


@pytest.mark.llnl
def test_llnl_search():
    results = check_search("https://esgf-node.llnl.gov/esg-search")
    for dsr in results:
        links = [
            fr.opendap_url
            for fr in dsr.file_context().search()
            if fr.opendap_url is not None
        ]
        if len(links) != dsr.number_of_files:
            raise ValueError(
                f"{dsr.dataset_id} number of files ({len(links)}) not equal to the results number ({dsr.number_of_links})"
            )


@pytest.mark.ornl
def test_ornl_file_core():
    check_file_core("esgf-node.ornl.gov")


@pytest.mark.ornl
@pytest.mark.performance
def test_ornl_search_speed():
    benchmark_search("https://esgf-node.ornl.gov/esg-search/", 1.11, 0.06)


@pytest.mark.llnl
@pytest.mark.performance
def test_llnl_search_speed():
    benchmark_search("https://esgf-node.llnl.gov/esg-search/", 0.74, 0.21)
