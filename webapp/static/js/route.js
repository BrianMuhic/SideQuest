// jshint esversion: 6
'use strict';

// -------------------------------------------------------------------------------------------------------------------
// Route API utilities - called by app.js
// -------------------------------------------------------------------------------------------------------------------

/**
 * Format a duration in minutes to a human-readable string.
 * @param {number} totalMinutes
 * @returns {string}
 */
function formatDuration(totalMinutes) {
    const hours   = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    if (hours > 0 && minutes > 0) return hours + ' hr ' + minutes + ' min';
    if (hours > 0) return hours + ' hr';
    return minutes + ' min';
}

/**
 * Fetch location autocomplete suggestions from the API.
 * @param {string} query
 * @param {Function} done - Receives the suggestions array on success
 * @returns {jqXHR}
 */
function fetchSuggestions(query, done) {
    return $.get({
        url: '/api/location-suggestions',
        data: { q: query, _: Date.now() },
        cache: false
    }).done(done);
}

/**
 * Fetch a route preview from the API.
 * @param {string} start - Start location label
 * @param {string} end - End location label
 * @returns {jqXHR}
 */
function fetchRoutePreview(start, end) {
    return $.get({
        url: '/api/route-preview',
        data: { start: start, end: end, _: Date.now() },
        cache: false
    });
}

/**
 * Save a route for the currently logged-in user.
 * @param {Object} payload
 * @returns {jqXHR}
 */
function saveRoute(payload) {
    return postJson('/api/saved-routes', payload);
}

/**
 * Fetch saved routes for the currently logged-in user.
 * @returns {jqXHR}
 */
function fetchSavedRoutes() {
    return $.get({
        url: '/api/saved-routes',
        data: { _: Date.now() },
        cache: false
    });
}
