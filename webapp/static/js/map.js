// jshint esversion: 6
'use strict';

// -------------------------------------------------------------------------------------------------------------------
// Map Utilities - shared Leaflet helpers used across OSM pages
// -------------------------------------------------------------------------------------------------------------------

/**
 * Create a Leaflet map pre-loaded with the OSM tile layer.
 * @param {string} elementId - ID of the container element
 * @param {number} lat - Initial latitude
 * @param {number} lng - Initial longitude
 * @param {number} zoom - Initial zoom level
 * @returns {L.Map}
 */
function osmMap(elementId, lat, lng, zoom) {
    const map = L.map(elementId).setView([lat, lng], zoom);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    return map;
}

/**
 * Draw a GeoJSON route on the map with the standard route style.
 * @param {L.Map} map
 * @param {object} geojson - GeoJSON object
 * @returns {L.GeoJSON}
 */
function mapRouteLayer(map, geojson) {
    return L.geoJSON(geojson, {
        style: { color: '#2563eb', weight: 5, opacity: 0.9 }
    }).addTo(map);
}

/**
 * Fit the map viewport to a layer's bounds.
 * @param {L.Map} map
 * @param {L.Layer} layer
 * @param {number[]} [padding=[50, 50]]
 */
function mapFitBounds(map, layer, padding) {
    const bounds = layer.getBounds();
    if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: padding || [50, 50] });
    }
}
