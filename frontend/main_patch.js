
// Replace existing isRealField with this:
function isRealField(p, key) {
    return p[key + "_source"] === "REAL";
}
