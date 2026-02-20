from pydantic import BaseModel
from typing import List, Optional, Any
import requests

from loguru import logger

import pandas as pd
from difflib import SequenceMatcher
import re


def general_search(
    df: pd.DataFrame,
    query: str,
    column_name: str,
    id_column: str,
    threshold: float = 0.8,
    top_k: int = 5,
    keep_columns: Optional[List[str]] = None,
) -> List[str]:
    """
    Takes a dataframe and returns the top_k matches for the query based on the column_name and id_column.

    Args:
        df (pd.DataFrame): The dataframe to search.
        query (str): The query to search for.
        column_name (str): The name of the column to search in.
        threshold (float, optional): The threshold for the fuzzy match. Defaults to 0.8.
        top_k (int, optional): The number of top matches to return. Defaults to 5.
        keep_columns (List[str], optional): List of column names to keep in results. If None, keeps all columns.
    """
    if df.empty or query.strip() == "":
        return []

    query_lower = query.lower().strip()
    matches = []

    for idx, row in df.iterrows():
        if pd.isna(row[column_name]):
            continue

        text = str(row[column_name]).lower().strip()
        similarity = calc_similarity(query_lower, text)

        if similarity >= threshold:
            row_dict = row.to_dict()
            if keep_columns is not None:
                row_dict = {
                    col: row_dict.get(col) for col in keep_columns if col in row_dict
                }
            row_dict["score"] = similarity
            matches.append(row_dict)

    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches


def strip_special_characters(text: str) -> str:
    """Strip special characters from text, keeping only alphanumeric and spaces."""
    return re.sub(r"[^a-zA-Z0-9\s]", "", text).strip()


def general_search_comma_list(
    df: pd.DataFrame,
    query: str,
    column_name: str,
    id_column: str,
    threshold: float = 0.8,
    top_k: int = 5,
    keep_columns: Optional[List[str]] = None,
) -> List[str]:
    """
    Takes a dataframe and returns the top_k matches for the query based on the column_name and id_column.
    Handles comma-separated lists in the column values and finds the best match within each list.
    Strips special characters before comparison.

    Args:
        df (pd.DataFrame): The dataframe to search.
        query (str): The query to search for.
        column_name (str): The name of the column to search in (contains comma-separated values).
        id_column (str): The name of the ID column.
        threshold (float, optional): The threshold for the fuzzy match. Defaults to 0.8.
        top_k (int, optional): The number of top matches to return. Defaults to 5.
        keep_columns (List[str], optional): List of column names to keep in results. If None, keeps all columns.
    """
    if df.empty or query.strip() == "":
        return []

    query_cleaned = strip_special_characters(query.lower())
    matches = []

    for idx, row in df.iterrows():
        if pd.isna(row[column_name]):
            continue

        # Split comma-separated values and find best match
        comma_list = str(row[column_name]).split(",")
        best_similarity = 0.0
        best_match_text = ""

        for item in comma_list:
            item_cleaned = strip_special_characters(item.lower())
            if item_cleaned:  # Skip empty items
                similarity = calc_similarity(query_cleaned, item_cleaned)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match_text = item.strip()

        if best_similarity >= threshold:
            row_dict = row.to_dict()
            if keep_columns is not None:
                row_dict = {
                    col: row_dict.get(col) for col in keep_columns if col in row_dict
                }
            row_dict["score"] = best_similarity
            row_dict["matched_text"] = best_match_text
            matches.append(row_dict)

    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches[:top_k]


def calc_similarity(query: str, text: str) -> float:
    return SequenceMatcher(None, query.lower().strip(), text.lower().strip()).ratio()


class VariantSearchResult(BaseModel):
    raw_input: str
    id: str
    name: str
    url: str
    score: float


"""
Searching PharmGKB API
"""


def pgkb_star_allele_search(
    star_allele: str, threshold: float = 0.8, top_k: int = 1
) -> Optional[List[VariantSearchResult]]:
    base_url = "https://api.pharmgkb.org/v1/data/haplotype?symbol="
    response = requests.get(base_url + star_allele)
    if response.status_code == 200:
        data = response.json()
        score = calc_similarity(star_allele, data["data"][0]["symbol"])
        if data["data"]:
            return [
                VariantSearchResult(
                    raw_input=star_allele,
                    id=result["id"],
                    name=result["symbol"],
                    url=f"https://www.clinpgx.org/haplotype/{result['id']}",
                    score=score,
                )
                for result in data["data"]
            ]
    return []


def pgkb_rsid_search(
    rsid: str, threshold: float = 0.8, top_k: int = 1
) -> Optional[List[VariantSearchResult]]:
    base_url = "https://api.pharmgkb.org/v1/data/variant?symbol="
    response = requests.get(base_url + rsid.strip())
    if response.status_code == 200:
        data = response.json()
        score = calc_similarity(rsid, data["data"][0]["symbol"])
        if data["data"]:
            return [
                VariantSearchResult(
                    raw_input=rsid,
                    id=result["id"],
                    name=result["symbol"],
                    url=f"https://www.clinpgx.org/variant/{result['id']}",
                    score=score,
                )
                for result in data["data"]
            ]
    return []


class VariantLookup(BaseModel):
    data_path: str = "lookup_data/variants/variants.tsv"

    def _clinpgx_variant_search(
        self, variant: str, threshold: float = 0.8, top_k: int = 1
    ) -> Optional[List[VariantSearchResult]]:
        """
        Search flow for variants
        1. Searches through the Variant Name column for similarity
        2. Searches through comma separated Synonyms column for similarity
        """
        df = pd.read_csv(self.data_path, sep="\t")
        results = general_search(
            df, variant, "Variant Name", "Variant ID", threshold=threshold, top_k=top_k
        )
        results.extend(
            general_search_comma_list(
                df, variant, "Synonyms", "Variant ID", threshold=threshold, top_k=top_k
            )
        )
        results.sort(key=lambda x: x["score"], reverse=True)
        if results:
            return [
                VariantSearchResult(
                    raw_input=variant,
                    id=result["Variant ID"],
                    name=result["Variant Name"],
                    url=f"https://www.clinpgx.org/variant/{result['Variant ID']}",
                    score=result["score"],
                )
                for result in results[:top_k]
            ]
        return []

    def star_lookup(
        self, star_allele: str, threshold: float = 0.8, top_k: int = 1
    ) -> Optional[List[VariantSearchResult]]:
        """
        Search flow for star alleles
        """
        results = pgkb_star_allele_search(star_allele, threshold=threshold, top_k=top_k)
        results.extend(
            self._clinpgx_variant_search(star_allele, threshold=threshold, top_k=top_k)
        )
        results.sort(key=lambda x: x.score, reverse=True)
        if results:
            return results[:top_k]
        return []

    def rsid_lookup(
        self, rsid: str, threshold: float = 0.8, top_k: int = 1
    ) -> Optional[List[VariantSearchResult]]:
        """
        Search flow for rsids
        """
        results = pgkb_rsid_search(rsid, threshold=threshold, top_k=top_k)
        results.extend(
            self._clinpgx_variant_search(rsid, threshold=threshold, top_k=top_k)
        )
        results.sort(key=lambda x: x.score, reverse=True)
        if results:
            return results[:top_k]
        return []

    def search(
        self, variant: str, threshold: float = 0.8, top_k: int = 1
    ) -> Optional[List[VariantSearchResult]]:
        # Check if it starts with "rs"
        if variant.strip().startswith("rs"):
            return self.rsid_lookup(variant, threshold=threshold, top_k=top_k)
        else:
            return self.star_lookup(variant, threshold=threshold, top_k=top_k)