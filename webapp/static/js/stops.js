'use strict';

function buildStopCard(stop, onAdd) {
    const category = stop.category || 'Stop';
    const name = stop.name || 'Unnamed stop';
    const address = stop.address || '';
    const description = stop.description || '';
    const detourMins = stop.detour_minutes != null ? stop.detour_minutes + ' min detour' : '';
    const detourMiles = stop.detour_miles != null ? stop.detour_miles + ' mi added' : '';
    const imageUrl = stop.photo_url || stop.image_url || '';

    const photoHtml = imageUrl
        ? '<div class="stop-photo stop-photo--image">' +
              '<img class="stop-photo-img" src="' + imageUrl + '" alt="' + name + '">' +
          '</div>'
        : '<div class="stop-photo">' + category + '</div>';

    const $card = $(
        '<div class="stop-card" data-stop-id="' + stop.id + '">' +
            photoHtml +
            '<div class="stop-body">' +
                '<div class="stop-meta">' +
                    '<span class="meta-badge">' + category + '</span>' +
                    '<span class="meta-badge">' + detourMins + '</span>' +
'                    <span class="meta-badge">' + detourMiles + '</span>' +
                '</div>' +
                '<div class="stop-title-row">' +
                    '<h3>' + name + '</h3>' +
                    '<button type="button" class="plus-button" aria-label="Add stop">+</button>' +
                '</div>' +
                '<p class="address">' + address + '</p>' +
                '<p class="description">' + description + '</p>' +
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