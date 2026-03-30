// jshint esversion: 6
'use strict';

// -------------------------------------------------------------------------------------------------------------------
// SPA Orchestrator
// Manages the map, panel state machine, and all inter-panel data flow.
// Depends on: map.js, route.js, stops.js
// -------------------------------------------------------------------------------------------------------------------

function initApp() {

    // -----------------------------------------------
    // Map
    // -----------------------------------------------

    const map = osmMap('map', 37.2296, -80.4139, 8);
    setTimeout(function() { map.invalidateSize(); }, 100);
    $(window).on('resize', function() { map.invalidateSize(); });

    // -----------------------------------------------
    // State
    // -----------------------------------------------

    let routeData     = null;  // data from /api/route-preview
    let routeLayer    = null;
    let startMarker   = null;
    let endMarker     = null;
    let stopMarkers   = {};    // stopId -> L.Marker
    let selectedStops = [];

    // -----------------------------------------------
    // Panel management
    // -----------------------------------------------

    function showPanel(id) {
        $('.panel').attr('hidden', true);
        $('#panel-' + id).removeAttr('hidden');
    }

    $('.panel .back').on('click', function() {
        var target = $(this).data('panel');

        if (target === 'stops') {
            clearDetailMarkers();
            drawRoute(routeData);
            selectedStops.forEach(function(stop) {
                var marker = L.marker([stop.lat, stop.lon])
                    .addTo(map).bindPopup('<strong>' + stop.name + '</strong><br>' + stop.category);
                stopMarkers[stop.id] = marker;
            });
        }

        showPanel(target);
    });

    // -----------------------------------------------
    // Route panel
    // -----------------------------------------------

    const $routeForm		= $('#route-form');
    const $startInput		= $('#start-location');
    const $endInput         = $('#end-location');
    const $startSuggestions = $('#start-suggestions');
    const $endSuggestions   = $('#end-suggestions');
    const $routeSummary     = $('#route-summary');
    const $routeFooter      = $('#route-footer');

    // Autocomplete helpers

    function hideSuggestions($list) {
        $list.empty().removeClass('show');
    }

    function renderSuggestions(items, $list, $input) {
        $list.empty();
        if (!items.length) { $list.removeClass('show'); return; }

        const rect = $input[0].getBoundingClientRect();
        $list.css({ top: rect.bottom + 6, left: rect.left, width: rect.width });

        items.forEach(function(item) {
            $('<li class="suggestions-item"></li>')
                .text(item.label)
                .on('mousedown', function(e) {
                    e.preventDefault();
                    $input.val(item.label);
                    hideSuggestions($list);
                })
                .appendTo($list);
        });

        $list.addClass('show');
    }

    function attachAutocomplete($input, $list) {
        let debounceTimer = null;
        let activeRequest = null;

        $input.on('input', function() {
            const query = $input.val().trim();
            if (activeRequest) { activeRequest.abort(); }
            clearTimeout(debounceTimer);

            if (query.length < 3) { hideSuggestions($list); return; }

            debounceTimer = setTimeout(function() {
                activeRequest = fetchSuggestions(query, function(items) {
                    renderSuggestions(items, $list, $input);
                });
            }, 250);
        });

        $input.on('blur', function() {
            setTimeout(function() { hideSuggestions($list); }, 150);
        });

        $input.on('focus', function() {
            if ($list.children().length) $list.addClass('show');
        });
    }

    attachAutocomplete($startInput, $startSuggestions);
    attachAutocomplete($endInput,   $endSuggestions);

    $(document).on('click', function(e) {
        if (!$(e.target).closest('.input-group').length) {
            hideSuggestions($startSuggestions);
            hideSuggestions($endSuggestions);
        }
    });

    // Route drawing

    function clearRouteLayer() {
        if (routeLayer)  { map.removeLayer(routeLayer);  routeLayer  = null; }
        if (startMarker) { map.removeLayer(startMarker); startMarker = null; }
        if (endMarker)   { map.removeLayer(endMarker);   endMarker   = null; }
    }

    function drawRoute(data) {
        clearRouteLayer();
        routeLayer  = mapRouteLayer(map, data.route);
        startMarker = L.marker([data.start.lat, data.start.lon])
            .addTo(map).bindPopup('<strong>Start</strong><br>' + data.start.name);
        endMarker   = L.marker([data.end.lat, data.end.lon])
            .addTo(map).bindPopup('<strong>End</strong><br>' + data.end.name);
        mapFitBounds(map, routeLayer);
    }

    // Route form submit

    let activeRouteRequest = null;

    $routeForm.on('submit', function(e) {
        e.preventDefault();

        const start = $startInput.val().trim();
        const end   = $endInput.val().trim();

        if (!start || !end) {
            $routeSummary.show().text('Please enter both a start and end destination.');
            return;
        }

        hideSuggestions($startSuggestions);
        hideSuggestions($endSuggestions);
        $routeFooter.attr('hidden', true);
        $routeSummary.show().addClass('loading-hint').text('Building route preview…');
        routeData = null;

        if (activeRouteRequest) activeRouteRequest.abort();

        activeRouteRequest = fetchRoutePreview(start, end)
            .done(function(data) {
                activeRouteRequest = null;
                routeData = data;
                drawRoute(data);
                $routeSummary.removeClass('loading-hint').show().html(
                    '<ul class="route-summary-list">' +
                    '<li><strong>Estimated Time:</strong> ' + formatDuration(data.duration_minutes) + '</li>' +
                    '<li><strong>Distance:</strong> ' + data.distance_miles + ' miles</li>' +
                    '</ul>'
                );
                $routeFooter.removeAttr('hidden');
            })
            .fail(function(xhr) {
                activeRouteRequest = null;
                if (xhr.statusText === 'abort') return;
                const d = xhr.responseJSON || {};
                $routeSummary.removeClass('loading-hint').show().text(d.error || 'Something went wrong while building the route.');
            });
    });

    // Advance to prefs panel

    $('#to-prefs-button').on('click', function() {
        if (!routeData) return;

        $('#prefs-trip-summary').html(
            '<div class="trip-summary-row"><strong>Start:</strong> '       + routeData.start.name + '</div>' +
            '<div class="trip-summary-row"><strong>Destination:</strong> ' + routeData.end.name   + '</div>' +
            '<div class="trip-summary-row"><strong>Drive Time:</strong> '  + formatDuration(routeData.duration_minutes) + '</div>' +
            '<div class="trip-summary-row"><strong>Distance:</strong> '    + routeData.distance_miles + ' miles</div>'
        );

        showPanel('prefs');
    });

    // -----------------------------------------------
    // Prefs panel
    // -----------------------------------------------

    $('#find-stops-button').on('click', function() {
        if (!routeData) return;

        const categories = [];
        $('input[name="stop_categories"]:checked').each(function() {
            categories.push($(this).val());
        });

        $('#find-stops-button').prop('disabled', true);
        $('#find-stops-loading').removeAttr('hidden');

        postJson('/api/find-stops', {
            start_location:          routeData.start.name,
            end_location:            routeData.end.name,
            duration_text:           formatDuration(routeData.duration_minutes),
            distance_text:           routeData.distance_miles + ' miles',
            latest_arrival_time:     $('#latest-arrival-time').val(),
            allowed_detour_hours:    parseInt($('#detour-hours').val()   || '0', 10),
            allowed_detour_minutes:  parseInt($('#detour-minutes').val() || '0', 10),
            stop_categories:         categories,
        }).done(function(data) {
            $('#find-stops-button').prop('disabled', false);
            $('#find-stops-loading').attr('hidden', true);
            renderStopsPanel(data);
            showPanel('stops');
        }).fail(function(xhr) {
            $('#find-stops-button').prop('disabled', false);
            $('#find-stops-loading').attr('hidden', true);
            if (xhr.statusText !== 'abort') {
                const d = xhr.responseJSON || {};
                alert(d.error || 'Unable to find stops. Please try again.');
            }
        });
    });

    // -----------------------------------------------
    // Stops panel
    // -----------------------------------------------

    function clearStopMarkers() {
        $.each(stopMarkers, function(id, marker) { map.removeLayer(marker); });
        stopMarkers   = {};
        selectedStops = [];
    }

    function renderSelectedStops() {
        const $list = $('#selected-list');
        const $btn  = $('#preview-route-button');

        if (!selectedStops.length) {
            $list.html('<p class="muted-text">No stops selected yet.</p>');
            $btn.prop('disabled', true);
            return;
        }

        $list.empty();
        $btn.prop('disabled', false);

        selectedStops.forEach(function(stop, index) {
            $('<div class="selected-item"></div>').html(
                '<div>' +
                '<div class="selected-item-name">'     + stop.name     + '</div>' +
                '<div class="selected-item-category">' + stop.category + '</div>' +
                '</div>' +
                '<button type="button" class="selected-remove" data-index="' + index + '">×</button>'
            ).appendTo($list);
        });

        $('.selected-remove').on('click', function() {
            const index   = Number($(this).data('index'));
            const removed = selectedStops[index];
            selectedStops.splice(index, 1);

            if (stopMarkers[removed.id]) {
                map.removeLayer(stopMarkers[removed.id]);
                delete stopMarkers[removed.id];
            }

            $('[data-stop-id="' + removed.id + '"] .plus-button').removeClass('added').text('+');
            renderSelectedStops();
        });
    }

    function renderStopsPanel(data) {
        clearStopMarkers();

        // Summary pills
        $('#stops-summary-pills').html(
            '<div class="summary-pill"><strong>Start:</strong> '        + routeData.start.name + '</div>' +
            '<div class="summary-pill"><strong>End:</strong> '          + routeData.end.name   + '</div>' +
            '<div class="summary-pill"><strong>Drive Time:</strong> '   + formatDuration(routeData.duration_minutes) + '</div>' +
            '<div class="summary-pill"><strong>Distance:</strong> '     + routeData.distance_miles + ' miles</div>' +
            (data.latest_arrival_time
                ? '<div class="summary-pill"><strong>Arrive by:</strong> ' + data.latest_arrival_time + '</div>'
                : '') +
            (data.allowed_detour_text
                ? '<div class="summary-pill"><strong>Detour:</strong> '    + data.allowed_detour_text + '</div>'
                : '')
        );

        // Stop cards
        const $feed = $('#stops-feed');
        $feed.empty();

        if (!data.stops || !data.stops.length) {
            $feed.html('<p class="muted-text">No stops found. Try adjusting your preferences.</p>');
            renderSelectedStops();
            return;
        }

        data.stops.forEach(function(stop) {
            $feed.append(buildStopCard(stop, function(addedStop) {
                selectedStops.push(addedStop);

                const marker = L.marker([addedStop.lat, addedStop.lon])
                    .addTo(map)
                    .bindPopup('<strong>' + addedStop.name + '</strong><br>' + addedStop.category);

                stopMarkers[addedStop.id] = marker;
                renderSelectedStops();
            }));
        });

        renderSelectedStops();
    }

    $('#preview-route-button').on('click', function() {
        if (!selectedStops.length) return;
        showRouteDetailPanel();
    });

    // -----------------------------------------------
    // Route detail panel
    // -----------------------------------------------

    let detailMarkers = [];

    function numberIcon(label, color) {
        return L.divIcon({
            className: 'route-number-marker',
            html: '<div class="route-marker-circle" style="background:' + color + '">' + label + '</div>',
            iconSize: [32, 32],
            iconAnchor: [16, 16]
        });
    }

    function clearDetailMarkers() {
        detailMarkers.forEach(function(m) { map.removeLayer(m); });
        detailMarkers = [];
    }

    function placeDetailMarkers() {
        clearDetailMarkers();
        $.each(stopMarkers, function(id, marker) { map.removeLayer(marker); });
        stopMarkers = {};

        detailMarkers.push(
            L.marker([routeData.start.lat, routeData.start.lon], { icon: numberIcon('A', '#16a34a') })
                .addTo(map).bindPopup('<strong>Start</strong><br>' + routeData.start.name)
        );

        selectedStops.forEach(function(stop, i) {
            detailMarkers.push(
                L.marker([stop.lat, stop.lon], { icon: numberIcon(String(i + 1), '#2563eb') })
                    .addTo(map).bindPopup('<strong>' + stop.name + '</strong><br>' + stop.category)
            );
        });

        detailMarkers.push(
            L.marker([routeData.end.lat, routeData.end.lon], { icon: numberIcon('B', '#dc2626') })
                .addTo(map).bindPopup('<strong>End</strong><br>' + routeData.end.name)
        );
    }

    function buildWaypoints() {
        var wps = [{ lat: routeData.start.lat, lon: routeData.start.lon }];
        selectedStops.forEach(function(s) { wps.push({ lat: s.lat, lon: s.lon }); });
        wps.push({ lat: routeData.end.lat, lon: routeData.end.lon });
        return wps;
    }

    function shortName(fullName) {
        var parts = fullName.split(',');
        return parts.length > 2 ? parts.slice(0, 2).join(',') : fullName;
    }

    function legRow(miles, minutes) {
        return '<div class="leg-connector">' +
               '<div class="leg-line"></div>' +
               '<span class="leg-detail">' + miles + ' mi &middot; ' + formatDuration(minutes) + '</span>' +
               '</div>';
    }

    function renderItinerary(legs) {
        var $el = $('#itinerary');
        $el.empty();

        $el.append(
            '<div class="itin-waypoint itin-waypoint--fixed">' +
            '<div class="itin-marker" style="background:#16a34a">A</div>' +
            '<div class="itin-info"><div class="itin-name">' + shortName(routeData.start.name) + '</div>' +
            '<div class="itin-label">Start</div></div></div>'
        );

        selectedStops.forEach(function(stop, i) {
            if (legs && legs[i]) {
                $el.append(legRow(legs[i].distance_miles, legs[i].duration_minutes));
            }

            var isFirst = (i === 0);
            var isLast  = (i === selectedStops.length - 1);

            $el.append(
                '<div class="itin-waypoint" data-index="' + i + '">' +
                '<div class="itin-marker" style="background:#2563eb">' + (i + 1) + '</div>' +
                '<div class="itin-info">' +
                  '<div class="itin-name">' + stop.name + '</div>' +
                  '<span class="meta-badge">' + stop.category + '</span>' +
                '</div>' +
                '<div class="itin-actions">' +
                  '<button type="button" class="itin-btn itin-move-up" data-index="' + i + '"' +
                    (isFirst ? ' disabled' : '') + ' aria-label="Move up">' +
                    '<i class="fa-solid fa-chevron-up"></i></button>' +
                  '<button type="button" class="itin-btn itin-move-down" data-index="' + i + '"' +
                    (isLast ? ' disabled' : '') + ' aria-label="Move down">' +
                    '<i class="fa-solid fa-chevron-down"></i></button>' +
                  '<button type="button" class="itin-btn itin-remove" data-index="' + i + '"' +
                    ' aria-label="Remove stop">' +
                    '<i class="fa-solid fa-xmark"></i></button>' +
                '</div></div>'
            );
        });

        if (legs && legs[selectedStops.length]) {
            $el.append(legRow(legs[selectedStops.length].distance_miles, legs[selectedStops.length].duration_minutes));
        }

        $el.append(
            '<div class="itin-waypoint itin-waypoint--fixed">' +
            '<div class="itin-marker" style="background:#dc2626">B</div>' +
            '<div class="itin-info"><div class="itin-name">' + shortName(routeData.end.name) + '</div>' +
            '<div class="itin-label">Destination</div></div></div>'
        );

        $('.itin-move-up').on('click', function() { moveDetailStop(Number($(this).data('index')), -1); });
        $('.itin-move-down').on('click', function() { moveDetailStop(Number($(this).data('index')), 1); });
        $('.itin-remove').on('click', function() { removeDetailStop(Number($(this).data('index'))); });
    }

    function renderDetailSummary(data) {
        $('#route-detail-summary').html(
            '<div class="route-detail-stat"><strong>Stops:</strong> ' + selectedStops.length + '</div>' +
            '<div class="route-detail-stat"><strong>Total Distance:</strong> ' + data.total_distance_miles + ' mi</div>' +
            '<div class="route-detail-stat"><strong>Total Drive Time:</strong> ' + formatDuration(data.total_duration_minutes) + '</div>'
        );
    }

    function fetchLegs() {
        postJson('/api/route-legs', { waypoints: buildWaypoints() })
            .done(function(data) {
                renderItinerary(data.legs);
                renderDetailSummary(data);
                updateAppleMapsLink();
            })
            .fail(function() {
                renderItinerary(null);
                $('#route-detail-summary').html(
                    '<p class="muted-text">Could not calculate route details.</p>'
                );
            });
    }

    function moveDetailStop(index, direction) {
        var newIndex = index + direction;
        if (newIndex < 0 || newIndex >= selectedStops.length) return;

        var temp = selectedStops[index];
        selectedStops[index] = selectedStops[newIndex];
        selectedStops[newIndex] = temp;

        placeDetailMarkers();
        fetchLegs();
    }

    function removeDetailStop(index) {
        selectedStops.splice(index, 1);

        if (!selectedStops.length) {
            showPanel('stops');
            renderSelectedStops();
            return;
        }

        placeDetailMarkers();
        fetchLegs();
    }

    function updateAppleMapsLink() {
        var saddr = routeData.start.lat + ',' + routeData.start.lon;
        var daddr = selectedStops.map(function(s) { return s.lat + ',' + s.lon; }).join('+to:');
        daddr += '+to:' + routeData.end.lat + ',' + routeData.end.lon;

        $('#apple-maps-link').attr('href',
            'https://maps.apple.com/?saddr=' + saddr + '&daddr=' + daddr + '&dirflg=d'
        );
    }

    function showRouteDetailPanel() {
        clearRouteLayer();
        routeLayer = mapRouteLayer(map, routeData.route);
        placeDetailMarkers();
        mapFitBounds(map, routeLayer);
        showPanel('route-detail');
        fetchLegs();
    }

    // -----------------------------------------------
    // Boot
    // -----------------------------------------------

    showPanel('route');
}
