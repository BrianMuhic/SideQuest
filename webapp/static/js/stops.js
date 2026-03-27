// jshint esversion: 6
'use strict';

// -------------------------------------------------------------------------------------------------------------------
// Stop card builder - called by app.js's renderStopsPanel
// -------------------------------------------------------------------------------------------------------------------

/**
 * Build and return a jQuery stop card element.
 * @param {object} stop - Stop data object from /api/find-stops
 * @param {Function} onAdd - Called with the stop object when the user clicks +
 * @returns {jQuery}
 */
function buildStopCard(stop, onAdd) {
    const photoHtml = stop.photo_url
        ? '<div class="stop-photo stop-photo--image">' +
              '<img class="stop-photo-img" src="' + stop.photo_url + '" alt="' + stop.name + '">' +
          '</div>'
        : '<div class="stop-photo">' + stop.category + '</div>';

    const $card = $(
        '<div class="stop-card" data-stop-id="' + stop.id + '">' +
        photoHtml +
        '<div class="stop-body">' +
          '<div class="stop-meta">' +
            '<span class="meta-badge">' + stop.category + '</span>' +
            '<span class="meta-badge">' + stop.distance_off_route_miles + ' mi off route</span>' +
          '</div>' +
          '<div class="stop-title-row">' +
            '<h3>' + stop.name + '</h3>' +
            '<button type="button" class="plus-button" aria-label="Add stop">+</button>' +
          '</div>' +
          '<p class="address">'     + stop.address     + '</p>' +
          '<p class="description">' + stop.description + '</p>' +
        '</div>' +
        '</div>'
    );

    $card.find('.plus-button').on('click', function() {
        if ($(this).hasClass('added')) return;
        $(this).addClass('added').text('✓');
        onAdd(stop);
    });

    return $card;
}
