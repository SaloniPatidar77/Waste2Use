console.log("Search script loaded ✅");

const searchInput = document.getElementById("searchInput");
const resultsDiv = document.querySelector(".search-results");

if (searchInput) {
  searchInput.addEventListener("keyup", async () => {
    let query = searchInput.value.trim();
    if (query.length > 0) {
      let response = await fetch(`/search?q=${encodeURIComponent(query)}`);
      let data = await response.text();
      // Server se jo HTML aayi usme se results part nikalo
      let parser = new DOMParser();
      let htmlDoc = parser.parseFromString(data, "text/html");
      let newResults = htmlDoc.querySelector(".search-results").innerHTML;
      resultsDiv.innerHTML = newResults;
    } else {
      resultsDiv.innerHTML = "";
    }
  });
}
