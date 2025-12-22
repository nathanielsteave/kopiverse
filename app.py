from flask import Flask, render_template, request
from SPARQLWrapper import SPARQLWrapper, JSON

app = Flask(__name__)

# Konfigurasi Fuseki
FUSEKI_ENDPOINT = "http://localhost:3030/kopiverse/query"

def get_sparql_results(query):
    sparql = SPARQLWrapper(FUSEKI_ENDPOINT)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    try:
        results = sparql.query().convert()
        return results["results"]["bindings"]
    except Exception as e:
        print(f"❌ Error Connection to Fuseki: {e}")
        return []

@app.route('/')
def welcome():
    return render_template('index.html')

@app.route('/role/<role_name>')
def role_dashboard(role_name):
    data = []
    page_title = ""
    # 1. FITUR BARU: Pencarian Universal (Lowercase agar case-insensitive)
    search_query = request.args.get('q', '').lower()

    # --- LOGIKA 1: PETANI ---
    if role_name == 'petani':
        page_title = "Dashboard Petani: Etalase Kebun"
        
        # Filter Pencarian untuk Petani
        filter_clause = ""
        if search_query:
            filter_clause = f"""
            FILTER (
                CONTAINS(LCASE(STR(?nama)), "{search_query}") || 
                CONTAINS(LCASE(STR(?panen)), "{search_query}") ||
                CONTAINS(LCASE(STR(?flavorLabel)), "{search_query}")
            )
            """

        query = f"""
        PREFIX : <http://kopiverse.org/ontology#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?lot ?nama ?harga ?panen ?organik ?score
               (GROUP_CONCAT(DISTINCT ?flavorLabel; separator=", ") AS ?flavors)
        WHERE {{
            ?lot a :CoffeeLot ; rdfs:label ?nama ; :hasPrice ?harga .
            OPTIONAL {{ ?lot :hasHarvestDate ?panen }}
            OPTIONAL {{ ?lot :isOrganic ?organik }}
            OPTIONAL {{ ?lot :hasCuppingScore ?score }}
            OPTIONAL {{ ?lot :hasFlavorNote ?f . ?f rdfs:label ?flavorLabel }}
            
            {filter_clause}
        }}
        GROUP BY ?lot ?nama ?harga ?panen ?organik ?score
        ORDER BY DESC(?harga)
        """
        
        results = get_sparql_results(query)
        for r in results:
            id_clean = r["lot"]["value"].split("#")[-1]
            try: h_val = f"Rp {float(r['harga']['value']):,.0f}"
            except: h_val = "Rp -"
            flavors = [f for f in r.get("flavors", {}).get("value", "").split(", ") if f]

            data.append({
                "id_clean": id_clean,
                "title": r["nama"]["value"],
                "price": h_val,
                "highlight": f"⭐ Score: {r.get('score', {}).get('value', '-')}",
                "detail_1": f"📅 Panen: {r.get('panen', {}).get('value', '-')}",
                "detail_2": f"🌱 Status: {'Organik' if r.get('organik', {}).get('value') == 'true' else 'Konvensional'}",
                "badges": flavors,
                "shop": None, "base_coffee": None
            })

    # --- LOGIKA 2: ROASTER ---
    elif role_name == 'roaster':
        page_title = "Dashboard Roaster: Sourcing & Profiling"
        
        # Filter Pencarian untuk Roaster (Bisa cari Origin, Proses, atau Grade)
        filter_clause = ""
        if search_query:
            filter_clause = f"""
            FILTER (
                CONTAINS(LCASE(STR(?nama)), "{search_query}") || 
                CONTAINS(LCASE(STR(?originName)), "{search_query}") ||
                CONTAINS(LCASE(STR(?processName)), "{search_query}") ||
                CONTAINS(LCASE(STR(?grade)), "{search_query}")
            )
            """

        query = f"""
        PREFIX : <http://kopiverse.org/ontology#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?lot ?nama ?moisture ?density ?profile ?originName ?price ?processName ?score
               ?screen ?aw ?stock ?crop ?defect ?agtron ?firstCrack ?dtr ?grade ?packaging
               ?ferm ?acid ?body ?shrink ?rest
               (GROUP_CONCAT(DISTINCT ?flavorLabel; separator=", ") AS ?flavors)
               (GROUP_CONCAT(DISTINCT ?certLabel; separator=", ") AS ?certs)
        WHERE {{
            ?lot a :CoffeeLot ; rdfs:label ?nama ; :hasDerivedOrigin ?o . ?o rdfs:label ?originName .
            
            OPTIONAL {{ ?lot :hasPrice ?price }}
            OPTIONAL {{ ?lot :hasMoistureContent ?moisture }}
            OPTIONAL {{ ?lot :hasBeanDensity ?density }}
            OPTIONAL {{ ?lot :recommendedRoastProfile ?profile }}
            OPTIONAL {{ ?lot :processedWith ?p . ?p rdfs:label ?processName }}
            OPTIONAL {{ ?lot :hasCuppingScore ?score }}
            OPTIONAL {{ ?lot :hasFlavorNote ?f . ?f rdfs:label ?flavorLabel }}
            OPTIONAL {{ ?lot :hasScreenSize ?screen }}
            OPTIONAL {{ ?lot :hasWaterActivity ?aw }}
            OPTIONAL {{ ?lot :hasStockKg ?stock }}
            OPTIONAL {{ ?lot :hasCropYear ?crop }}
            OPTIONAL {{ ?lot :hasDefectCount ?defect }}
            OPTIONAL {{ ?lot :hasBeanGrade ?grade }}
            OPTIONAL {{ ?lot :packagingType ?packaging }}
            OPTIONAL {{ ?lot :hasAgtronNumber ?agtron }}
            OPTIONAL {{ ?lot :hasFirstCrackTemp ?firstCrack }}
            OPTIONAL {{ ?lot :recommendedDTR ?dtr }}
            OPTIONAL {{ ?lot :hasShrinkage ?shrink }}
            OPTIONAL {{ ?lot :restingDays ?rest }}
            OPTIONAL {{ ?lot :fermentationHours ?ferm }}
            OPTIONAL {{ ?lot :acidityLevel ?acid }}
            OPTIONAL {{ ?lot :bodyLevel ?body }}
            OPTIONAL {{ ?lot :hasCertification ?c . ?c rdfs:label ?certLabel }}
            
            {filter_clause}
        }}
        GROUP BY ?lot ?nama ?moisture ?density ?profile ?originName ?price ?processName ?score 
                 ?screen ?aw ?stock ?crop ?defect ?agtron ?firstCrack ?dtr ?grade ?packaging
                 ?ferm ?acid ?body ?shrink ?rest
        """
        results = get_sparql_results(query)
        for r in results:
            id_clean = r["lot"]["value"].split("#")[-1]
            try: h_val = f"Rp {float(r.get('price', {}).get('value', 0)):,.0f}"
            except: h_val = "Call"

            flavors = [f for f in r.get("flavors", {}).get("value", "").split(", ") if f]
            certs = [c for c in r.get("certs", {}).get("value", "").split(", ") if c]
            stock_val = int(r.get("stock", {}).get("value", 0)) if r.get("stock") else 0
            
            stock_status = "Available"
            if stock_val < 100: stock_status = "Low Stock"
            if stock_val == 0: stock_status = "Out of Stock"

            proc_name = r.get("processName", {}).get("value", "-")
            prof_name = r.get("profile", {}).get("value", "-")

            data.append({
                "id_clean": id_clean,
                "title": r["nama"]["value"],
                "price": h_val,
                "origin": r["originName"]["value"],
                "process": proc_name,
                "highlight": f"📦 Stock: {stock_val} Kg",
                "stock_status": stock_status,
                "detail_1": f"⚙️ {proc_name}",  
                "detail_2": f"🔥 {prof_name}",
                "specs": {
                    "moisture": r.get("moisture", {}).get("value"),
                    "aw": r.get("aw", {}).get("value"),
                    "defect": r.get("defect", {}).get("value"),
                    "crop": r.get("crop", {}).get("value"),
                    "screen": r.get("screen", {}).get("value"),
                    "grade": r.get("grade", {}).get("value"),
                    "packaging": r.get("packaging", {}).get("value"),
                    "agtron": r.get("agtron", {}).get("value"),
                    "first_crack": r.get("firstCrack", {}).get("value"),
                    "dtr": r.get("dtr", {}).get("value"),
                    "shrink": r.get("shrink", {}).get("value"),
                    "rest": r.get("rest", {}).get("value"),
                    "ferm": r.get("ferm", {}).get("value"),
                    "acid": r.get("acid", {}).get("value"),
                    "body": r.get("body", {}).get("value"),
                    "certs": certs
                },
                "score": r.get("score", {}).get("value"),
                "badges": flavors,
                "shop": None, "base_coffee": None
            })

    # --- LOGIKA 3: BARISTA ---
    elif role_name == 'barista':
        page_title = "Dashboard Barista: Menu & Brewing Guide"
        filter_clause = ""
        if search_query:
            filter_clause = f"""FILTER (CONTAINS(LCASE(STR(?nama)), "{search_query}") || CONTAINS(LCASE(STR(?ingLabel)), "{search_query}") || CONTAINS(LCASE(STR(?flavorLabel)), "{search_query}"))"""

        query = f"""
        PREFIX : <http://kopiverse.org/ontology#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?bev ?nama ?desc ?shopName ?baseName ?temp ?time ?ratio ?price
               (GROUP_CONCAT(DISTINCT ?ingLabel; separator=", ") AS ?ingredients)
               (GROUP_CONCAT(DISTINCT ?flavorLabel; separator=", ") AS ?flavors)
        WHERE {{
            ?bev a :CoffeeBeverage ; rdfs:label ?nama .
            OPTIONAL {{ ?bev :hasPrice ?price }}
            OPTIONAL {{ ?bev rdfs:comment ?desc }}
            OPTIONAL {{ ?bev :servedBy ?shop . ?shop rdfs:label ?shopName }}
            OPTIONAL {{ ?bev :brewedFrom ?base . BIND(COALESCE(?baseLabelRaw, STRAFTER(STR(?base), "#")) AS ?baseName) OPTIONAL {{ ?base rdfs:label ?baseLabelRaw }} }}
            OPTIONAL {{ ?bev :hasIngredient ?ing . BIND(COALESCE(?ingLabelRaw, STRAFTER(STR(?ing), "#")) AS ?ingLabel) OPTIONAL {{ ?ing rdfs:label ?ingLabelRaw }} }}
            OPTIONAL {{ ?bev :hasFlavorNote ?f . ?f rdfs:label ?flavorLabel }}
            OPTIONAL {{ ?bev :brewingTemp ?temp }} OPTIONAL {{ ?bev :brewingTime ?time }} OPTIONAL {{ ?bev :waterRatio ?ratio }}
            {filter_clause}
        }}
        GROUP BY ?bev ?nama ?desc ?shopName ?baseName ?temp ?time ?ratio ?price
        ORDER BY ?nama
        """
        results = get_sparql_results(query)
        for r in results:
            id_clean = r["bev"]["value"].split("#")[-1]
            try: h_val = f"Rp {float(r.get('price', {}).get('value', 0)):,.0f}"
            except: h_val = "Ask Barista"
            ing = [i for i in r.get("ingredients", {}).get("value", "").split(", ") if i]
            flav = [f for f in r.get("flavors", {}).get("value", "").split(", ") if f]

            data.append({
                "id_clean": id_clean,
                "title": r["nama"]["value"],
                "price": h_val,
                "description": r.get("desc", {}).get("value"),
                "shop": r.get("shopName", {}).get("value"),
                "base_coffee": r.get("baseName", {}).get("value"),
                "specs": {"temp": r.get("temp", {}).get("value"), "time": r.get("time", {}).get("value"), "ratio": r.get("ratio", {}).get("value")},
                "ingredients": ing, "badges": flav
            })

    return render_template('role_view.html', data=data, title=page_title, role=role_name, search_query=search_query)

# --- ROUTE DETAIL ---
@app.route('/detail/<path:product_id>')
def detail_page(product_id):
    # Query Utama (Detail Produk)
    query = f"""
    PREFIX : <http://kopiverse.org/ontology#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?s ?nama ?desc ?price ?score ?shopName ?farmName ?altitude ?processName ?originName ?harvest ?moisture ?density ?roastProfile ?temp ?time ?ratio ?baseName ?originURI
           (GROUP_CONCAT(DISTINCT ?ingLabel; separator=", ") AS ?ingredients)
           (GROUP_CONCAT(DISTINCT ?flavorLabel; separator=", ") AS ?flavors)
    WHERE {{
        BIND(:{product_id} AS ?s)
        ?s rdfs:label ?nama .
        OPTIONAL {{ ?s rdfs:comment ?desc }}
        OPTIONAL {{ ?s :hasPrice ?price }}
        OPTIONAL {{ ?s :hasCuppingScore ?score }}
        OPTIONAL {{ ?s :servedBy ?shop . ?shop rdfs:label ?shopName }}
        OPTIONAL {{ ?s :brewingTemp ?temp }} OPTIONAL {{ ?s :brewingTime ?time }} OPTIONAL {{ ?s :waterRatio ?ratio }}
        OPTIONAL {{ ?s :brewedFrom ?base . BIND(COALESCE(?baseLabelRaw, STRAFTER(STR(?base), "#")) AS ?baseName) OPTIONAL {{ ?base rdfs:label ?baseLabelRaw }} }}
        OPTIONAL {{ ?s :hasIngredient ?ing . BIND(COALESCE(?ingLabelRaw, STRAFTER(STR(?ing), "#")) AS ?ingLabel) OPTIONAL {{ ?ing rdfs:label ?ingLabelRaw }} }}
        OPTIONAL {{ ?s :producedBy ?farm . ?farm rdfs:label ?farmName . OPTIONAL {{ ?farm :hasAltitude ?altitude }} }}
        OPTIONAL {{ ?s :processedWith ?p . ?p rdfs:label ?processName }}
        OPTIONAL {{ ?s :hasDerivedOrigin ?o . ?o rdfs:label ?originName . BIND(?o AS ?originURI) }}
        OPTIONAL {{ ?s :hasHarvestDate ?harvest }}
        OPTIONAL {{ ?s :hasMoistureContent ?moisture }}
        OPTIONAL {{ ?s :hasBeanDensity ?density }}
        OPTIONAL {{ ?s :recommendedRoastProfile ?roastProfile }}
        OPTIONAL {{ ?s :hasFlavorNote ?f . ?f rdfs:label ?flavorLabel }}
    }}
    GROUP BY ?s ?nama ?desc ?price ?score ?shopName ?farmName ?altitude ?processName ?originName ?harvest ?moisture ?density ?roastProfile ?temp ?time ?ratio ?baseName ?originURI
    """
    results = get_sparql_results(query)
    if not results: return "Data not found"
    
    r = results[0]
    
    # 2. FITUR BARU: QUERY REKOMENDASI (Produk Serupa)
    # Mencari produk lain yang memiliki Origin SAMA atau Proses SAMA, tapi bukan produk ini.
    origin_uri = r.get("originURI", {}).get("value")
    recommendations = []
    
    if origin_uri:
        rec_query = f"""
        PREFIX : <http://kopiverse.org/ontology#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?rec ?recName ?recPrice ?recOrigin
        WHERE {{
            ?rec :hasDerivedOrigin <{origin_uri}> .
            ?rec rdfs:label ?recName .
            OPTIONAL {{ ?rec :hasPrice ?recPrice }}
            FILTER (?rec != <{r["s"]["value"]}>)
        }} LIMIT 3
        """
        rec_results = get_sparql_results(rec_query)
        for rec in rec_results:
            rec_id = rec["rec"]["value"].split("#")[-1]
            try: rec_price = f"Rp {float(rec.get('recPrice', {}).get('value', 0)):,.0f}"
            except: rec_price = "-"
            recommendations.append({"id": rec_id, "name": rec["recName"]["value"], "price": rec_price})

    try: h_fmt = f"Rp {float(r.get('price', {}).get('value', 0)):,.0f}"
    except: h_fmt = None
    
    info = {
        "nama": r["nama"]["value"],
        "description": r.get("desc", {}).get("value"),
        "harga": h_fmt,
        "skor": r.get("score", {}).get("value"),
        "shop": r.get("shopName", {}).get("value"),
        "farm": r.get("farmName", {}).get("value"),
        "altitude": r.get("altitude", {}).get("value"),
        "origin": r.get("originName", {}).get("value"),
        "process": r.get("processName", {}).get("value"),
        "harvest": r.get("harvest", {}).get("value"),
        "moisture": r.get("moisture", {}).get("value"),
        "density": r.get("density", {}).get("value"),
        "roast_profile": r.get("roastProfile", {}).get("value"),
        "base_coffee": r.get("baseName", {}).get("value"),
        "specs": {
            "temp": r.get("temp", {}).get("value"),
            "time": r.get("time", {}).get("value"),
            "ratio": r.get("ratio", {}).get("value")
        },
        "ingredients": [i for i in r.get("ingredients", {}).get("value", "").split(", ") if i],
        "badges": [f for f in r.get("flavors", {}).get("value", "").split(", ") if f],
        "recommendations": recommendations # Data rekomendasi dikirim ke template
    }
    return render_template('detail.html', info=info)

if __name__ == '__main__':
    app.run(debug=True)