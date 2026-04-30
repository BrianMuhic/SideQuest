'use strict';

function defaultImageForCategory(category) {
    var cat = (category || '').toLowerCase();
    if (cat.indexOf('coffee') !== -1 || cat.indexOf('cafe') !== -1)
        return 'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?auto=format&fit=crop&w=900&q=80';
    if (cat.indexOf('restaurant') !== -1 || cat.indexOf('food') !== -1)
        return 'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=900&q=80';
    if (cat.indexOf('park') !== -1 || cat.indexOf('hike') !== -1 || cat.indexOf('trail') !== -1)
        return 'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=900&q=80';
    if (cat.indexOf('museum') !== -1)
        return 'https://images.unsplash.com/photo-1565060169187-6f5f06e1f3ec?auto=format&fit=crop&w=900&q=80';
    if (cat.indexOf('attraction') !== -1 || cat.indexOf('landmark') !== -1)
        return 'https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=900&q=80';
    if (cat.indexOf('shopping') !== -1 || cat.indexOf('store') !== -1)
        return 'https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&w=900&q=80';
    if (cat.indexOf('hotel') !== -1 || cat.indexOf('lodging') !== -1)
        return 'https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=900&q=80';
    return 'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=900&q=80';
}

function buildStopCard(stop, onAdd) {
    const category = stop.category || 'Stop';
    const name = stop.name || 'Unnamed stop';
    const address = stop.address || '';
    const description = stop.description || '';
    const detourMins = stop.detour_minutes != null ? stop.detour_minutes + ' min detour' : '';
    const detourMiles = stop.detour_miles != null ? stop.detour_miles + ' mi added' : '';
    const imageUrl = stop.photo_url || stop.image_url || defaultImageForCategory(stop.category);

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

(function() {
    var _inFlight = 0;
    var _queue = [];
    var _MAX = 4;

    function _flush() {
        while (_inFlight < _MAX && _queue.length) {
            var item = _queue.shift();
            _inFlight++;
            var params = new URLSearchParams({
                name:    item.stop.name    || '',
                address: item.stop.address || '',
                lat:     item.stop.lat,
                lon:     item.stop.lon,
            });
            fetch('/api/stop-photo?' + params)
                .then(function(r) { return r.ok ? r.json() : null; })
                .then(function(data) {
                    if (data && data.photo_url) {
                        item.$card.find('.stop-photo-img').attr('src', data.photo_url);
                    }
                })
                .catch(function() {})
                .finally(function() {
                    _inFlight--;
                    _flush();
                });
        }
    }

    window.lazyLoadStopPhoto = function(stop, $card) {
        if (stop.photo_url || stop.image_url) return;
        _queue.push({ stop: stop, $card: $card });
        _flush();
    };
}());
