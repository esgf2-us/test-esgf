import random

import requests
from tqdm import tqdm


def esg_search(base_url, **search):
    """Yields paginated responses using the ESGF REST API."""
    if "format" not in search:
        search["format"] = "application/solr+json"
    response = requests.get(base_url, params=search)
    response.raise_for_status()
    response = response.json()
    return response


fastapi_url = "https://ci-setup-esgf-esg-fastapi.mariner-cluster.ornl.gov"
solr_url = "https://esgf-node.ornl.gov/esg-search/search"


r = esg_search(solr_url, experiment_id=["historical", "piControl"], limit=0, facets="*")
facets = {}
for facet in r["facet_counts"]["facet_fields"]:
    facets[facet] = r["facet_counts"]["facet_fields"][facet][::2]

for facet, values in tqdm(facets.items()):

    # The facet actually needs some values, pick a random one
    if not values:
        continue
    search = {facet: random.sample(values, 1)}

    # Solr response
    r_solr = esg_search(solr_url, **search)
    n_solr = r_solr["response"]["numFound"]

    # FastAPI response
    r_fastapi = esg_search(fastapi_url, **search)
    n_fastapi = r_fastapi["response"]["numFound"]
    if n_solr != n_fastapi:
        tqdm.write(f"{search}")
