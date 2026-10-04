import re
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class WasteIdeaModel:

    def __init__(self, csv_path="data/waste_ideas.csv"):

        self.df = pd.read_csv(csv_path)

        # Empty values handle karo
        for column in ["title", "material", "description"]:
            self.df[column] = (
                self.df[column]
                .fillna("")
                .astype(str)
            )

        # Search ke liye combined text
        self.df["combined"] = (
            self.df["title"] + " " +
            self.df["material"] + " " +
            self.df["description"]
        )

        # TF-IDF search model
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2)
        )

        self.tfidf_matrix = self.vectorizer.fit_transform(
            self.df["combined"]
        )

        # Hindi / Hinglish / English keywords
        self.keyword_map = {

            # =========================
            # PLASTIC
            # =========================
            "plastic": "Plastic",
            "bottle": "Plastic",
            "bottles": "Plastic",
            "plastic bottle": "Plastic",
            "plastic bottles": "Plastic",
            "old bottle": "Plastic",
            "old bottles": "Plastic",
            "waste bottle": "Plastic",
            "waste bottles": "Plastic",
            "water bottle": "Plastic",
            "water bottles": "Plastic",
            "pet bottle": "Plastic",
            "pet bottles": "Plastic",

            # =========================
            # CLOTH
            # =========================
            "cloth": "Cloth",
            "clothes": "Cloth",
            "kapda": "Cloth",
            "kapde": "Cloth",
            "kapda waste": "Cloth",
            "kapde waste": "Cloth",
            "old clothes": "Cloth",
            "old cloth": "Cloth",
            "tshirt": "Cloth",
            "t-shirt": "Cloth",
            "t shirts": "Cloth",
            "t-shirts": "Cloth",
            "jeans": "Cloth",
            "old jeans": "Cloth",
            "denim": "Cloth",
            "fabric": "Cloth",
            "old fabric": "Cloth",
            "shirt": "Cloth",
            "old shirt": "Cloth",

            # =========================
            # PAPER
            # =========================
            "paper": "Paper",
            "papers": "Paper",
            "kagaz": "Paper",
            "kagaz waste": "Paper",
            "newspaper": "Paper",
            "newspapers": "Paper",
            "news paper": "Paper",
            "old newspaper": "Paper",
            "old newspapers": "Paper",
            "magazine": "Paper",
            "magazines": "Paper",

            # =========================
            # RUBBER / TYRE
            # =========================
            "rubber": "Rubber",
            "tyre": "Rubber",
            "tyres": "Rubber",
            "tire": "Rubber",
            "tires": "Rubber",
            "old tyre": "Rubber",
            "old tyres": "Rubber",
            "old tire": "Rubber",
            "old tires": "Rubber",
            "waste tyre": "Rubber",
            "waste tires": "Rubber",

            # =========================
            # TIN
            # =========================
            "tin": "Tin",
            "tin can": "Tin",
            "tin cans": "Tin",
            "tin container": "Tin",
            "metal can": "Tin",

            # =========================
            # CARDBOARD
            # =========================
            "cardboard": "Cardboard",
            "card board": "Cardboard",
            "cardboard box": "Cardboard",
            "cardboard boxes": "Cardboard",
            "waste cardboard": "Cardboard",
            "old cardboard": "Cardboard",
            "carton": "Cardboard",
            "carton box": "Cardboard",

            # =========================
            # COCONUT
            # =========================
            "coconut": "Coconut",
            "coconuts": "Coconut",
            "nariyal": "Coconut",
            "coconut shell": "Coconut",
            "coconut shells": "Coconut",
            "nariyal ka chilka": "Coconut",
            "nariyal shell": "Coconut",
            "coconut waste": "Coconut",

            # =========================
            # GLASS
            # =========================
            "glass": "Glass",
            "glass jar": "Glass",
            "glass jars": "Glass",
            "glass bottle": "Glass",
            "glass bottles": "Glass",
            "old glass": "Glass",
            "old jar": "Glass",
            "old jars": "Glass",

            # =========================
            # METAL
            # =========================
            "metal": "Metal",
            "metal can": "Metal",
            "metal cans": "Metal",
            "old metal": "Metal",
            "metal container": "Metal",
            "metal containers": "Metal",

            # =========================
            # WOOD
            # =========================
            "wood": "Wood",
            "wooden": "Wood",
            "wooden box": "Wood",
            "wooden boxes": "Wood",
            "wooden crate": "Wood",
            "wooden crates": "Wood",
            "wood scrap": "Wood",
            "wood scraps": "Wood",
            "old wood": "Wood",
            "wooden piece": "Wood",
            "wooden pieces": "Wood",
        }

    # =========================================
    # NORMALIZE QUERY
    # =========================================

    def normalize_query(self, query):

        query = str(query).lower().strip()

        query = " ".join(query.split())

        return query

    # =========================================
    # DETECT ONE MATERIAL
    # =========================================

    def detect_material(self, query):

        query = self.normalize_query(query)

        phrases = sorted(
            self.keyword_map.items(),
            key=lambda x: len(x[0]),
            reverse=True
        )

        for keyword, material in phrases:

            pattern = r"\b" + re.escape(keyword) + r"\b"

            if re.search(pattern, query):
                return material

        return None

    # =========================================
    # DETECT MULTIPLE MATERIALS
    # =========================================

    def detect_materials(self, query):

        query = self.normalize_query(query)

        detected = []

        phrases = sorted(
            self.keyword_map.items(),
            key=lambda x: len(x[0]),
            reverse=True
        )

        for keyword, material in phrases:

            pattern = r"\b" + re.escape(keyword) + r"\b"

            if re.search(pattern, query):

                if material not in detected:
                    detected.append(material)

        return detected

    # =========================================
    # MULTIPLE MATERIAL SEARCH
    # =========================================

    def search_multiple_materials(self, query):

        query = self.normalize_query(query)

        if not query:
            return []

        materials = self.detect_materials(query)

        if not materials:
            return self.similarity_search(query)

        filtered_df = self.df[
            self.df["material"].isin(materials)
        ].copy()

        if filtered_df.empty:
            return []

        query_vector = self.vectorizer.transform([query])

        filtered_indices = filtered_df.index.tolist()

        scores = cosine_similarity(
            query_vector,
            self.tfidf_matrix[filtered_indices]
        ).flatten()

        filtered_df["score"] = scores

        filtered_df = filtered_df.sort_values(
            by="score",
            ascending=False
        )
        filtered_df = filtered_df.head(5)

        return filtered_df[
            [
                "id",
                "title",
                "material",
                "description",
                "image"
            ]
        ].to_dict(orient="records")

    # =========================================
    # MAIN SEARCH
    # =========================================

    def search(self, query):

        query = self.normalize_query(query)

        if not query:
            return []

        material = self.detect_material(query)

        if material:

            filtered_df = self.df[
                self.df["material"].str.lower()
                == material.lower()
            ].copy()

            if filtered_df.empty:
                return []

            query_vector = self.vectorizer.transform([query])

            filtered_indices = filtered_df.index.tolist()

            scores = cosine_similarity(
                query_vector,
                self.tfidf_matrix[filtered_indices]
            ).flatten()

            filtered_df["score"] = scores

            filtered_df = filtered_df.sort_values(
                by="score",
                ascending=False
            )

            return filtered_df[
                [
                    "id",
                    "title",
                    "material",
                    "description",
                    "image"
                ]
            ].to_dict(orient="records")

        return self.similarity_search(query)

    # =========================================
    # TF-IDF SIMILARITY SEARCH
    # =========================================

    def similarity_search(self, query):

        query_vector = self.vectorizer.transform([query])

        cosine_sim = cosine_similarity(
            query_vector,
            self.tfidf_matrix
        ).flatten()

        top_indices = cosine_sim.argsort()[::-1]

        results = []

        for index in top_indices:

            if cosine_sim[index] <= 0:
                continue

            row = self.df.iloc[index]

            results.append({
                "id": row["id"],
                "title": row["title"],
                "material": row["material"],
                "description": row["description"],
                "image": row["image"]
            })

            if len(results) == 5:
                break

        return results