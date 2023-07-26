import re

import requests
import json
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


def check_search(esg_search: str):
    """Given the connection for the search, use pyesgf to check search results."""
    conn = SearchConnection(esg_search, distrib=False)
    ctx = conn.new_context(
        facets=[
            "data_node",
            "project",
            "experiment_id",
            "source_id",
            "member_id",
            "grid_label",
            "frequency",
            "variable_id",
        ],
        data_node="esgf-node.ornl.gov" if "ornl" in conn.url else None,
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


def check_file_core(core):
    file_url = f"https://{core}/esg-search/search?type=File&distrib=false&limit=0&format=application%2fsolr%2bjson"
    resp = requests.get(file_url)
    
    numfound = resp.json()["response"]["numFound"] 
    if numfound < EXPECTED_FILES:
        raise ValueError(f"At {core}: {numfound} files found, below the {EXPECTED_FILES} threshold.")


def test_ornl_search():
    check_search("https://esgf-node.ornl.gov/esg-search/")


def test_llnl_search():
    check_search("https://esgf-node.llnl.gov/esg-search")


def test_ornl_file_core():
    check_file_core("esgf-node.ornl.gov")
