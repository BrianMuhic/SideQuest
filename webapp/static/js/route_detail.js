// jshint esversion: 6
'use strict';

// -------------------------------------------------------------------------------------------------------------------
// Route Detail Page
// Reads route + selected stops from sessionStorage, renders the itinerary with per-leg details,
// and provides reorder, remove, and Apple Maps export.
// Depends on: map.js, route.js, utils.js
// -------------------------------------------------------------------------------------------------------------------

function initRouteDetail() {

    var rawRoute = sessionStorage.getItem('sidequest_route');
    var rawStops = sessionStorage.getItem('sidequest_stops');

    if (!rawRoute || !rawStops) {
        window.location.href = '/';
        return;
    }

    var routeData = JSON.parse(rawRoute);
    var stops     = JSON.parse(rawStops);

    if (!stops.length) {
        window.location.href = '/';
        return;
    }

    // -----------------------------------------------
    // Map
    // -----------------------------------------------

    var map = osmMap('map', routeData.start.lat, routeData.start.lon, 8);
    setTimeout(function() { map.invalidateSize(); }, 100);
    $(window).on('resize', function() { map.invalidateSize(); });

    var routeLayer = mapRouteLayer(map, routeData.route);
    mapFitBounds(map, routeLayer);

    // -----------------------------------------------
    // Markers
    // -----------------------------------------------

    var markers = [];

    function numberIcon(label, color) {
        return L.divIcon({
            className: 'route-number-marker',
            html: '<div class="route-marker-circle" style="background:' + color + '">' + label + '</div>',
            iconSize: [32, 32],
            iconAnchor: [16, 16]
        });
    }

    function clearMarkers() {
        markers.forEach(function(m) { map.removeLayer(m); });
        markers = [];
    }

    function placeMarkers() {
        clearMarkers();

        var startM = L.marker([routeData.start.lat, routeData.start.lon], {
            icon: numberIcon('A', '#16a34a')
        }).addTo(map).bindPopup('<strong>Start</strong><br>' + routeData.start.name);
        markers.push(startM);

        stops.forEach(function(stop, i) {
            var m = L.marker([stop.lat, stop.lon], {
                icon: numberIcon(String(i + 1), '#2563eb')
            }).addTo(map).bindPopup('<strong>' + stop.name + '</strong><br>' + stop.category);
            markers.push(m);
        });

        var endM = L.marker([routeData.end.lat, routeData.end.lon], {
            icon: numberIcon('B', '#dc2626')
        }).addTo(map).bindPopup('<strong>End</strong><br>' + routeData.end.name);
        markers.push(endM);
    }

    placeMarkers();

    // -----------------------------------------------
    // Waypoint builder
    // -----------------------------------------------

    function buildWaypoints() {
        var wps = [{ lat: routeData.start.lat, lon: routeData.start.lon }];
        stops.forEach(function(s) { wps.push({ lat: s.lat, lon: s.lon }); });
        wps.push({ lat: routeData.end.lat, lon: routeData.end.lon });
        return wps;
    }

    // -----------------------------------------------
    // Itinerary rendering
    // -----------------------------------------------

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

        // Start waypoint
        $el.append(
            '<div class="itin-waypoint itin-waypoint--fixed">' +
            '<div class="itin-marker" style="background:#16a34a">A</div>' +
            '<div class="itin-info"><div class="itin-name">' + shortName(routeData.start.name) + '</div>' +
            '<div class="itin-label">Start</div></div>' +
            '</div>'
        );

        // Stops with leg connectors
        stops.forEach(function(stop, i) {
            if (legs && legs[i]) {
                $el.append(legRow(legs[i].distance_miles, legs[i].duration_minutes));
            }

            var isFirst = (i === 0);
            var isLast  = (i === stops.length - 1);

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
                '</div>' +
                '</div>'
            );
        });

        // Last leg connector
        if (legs && legs[stops.length]) {
            $el.append(legRow(legs[stops.length].distance_miles, legs[stops.length].duration_minutes));
        }

        // End waypoint
        $el.append(
            '<div class="itin-waypoint itin-waypoint--fixed">' +
            '<div class="itin-marker" style="background:#dc2626">B</div>' +
            '<div class="itin-info"><div class="itin-name">' + shortName(routeData.end.name) + '</div>' +
            '<div class="itin-label">Destination</div></div>' +
            '</div>'
        );

        // Wire button events
        $('.itin-move-up').on('click', function() { moveStop(Number($(this).data('index')), -1); });
        $('.itin-move-down').on('click', function() { moveStop(Number($(this).data('index')), 1); });
        $('.itin-remove').on('click', function() { removeStop(Number($(this).data('index'))); });
    }

    function renderSummary(data) {
        $('#route-detail-summary').html(
            '<div class="route-detail-stat"><strong>Stops:</strong> ' + stops.length + '</div>' +
            '<div class="route-detail-stat"><strong>Total Distance:</strong> ' + data.total_distance_miles + ' mi</div>' +
            '<div class="route-detail-stat"><strong>Total Drive Time:</strong> ' + formatDuration(data.total_duration_minutes) + '</div>'
        );
    }

    // -----------------------------------------------
    // Fetch legs from API
    // -----------------------------------------------

    function fetchLegs() {
        var waypoints = buildWaypoints();

        postJson('/api/route-legs', { waypoints: waypoints })
            .done(function(data) {
                renderItinerary(data.legs);
                renderSummary(data);
                updateAppleMapsLink();
            })
            .fail(function() {
                renderItinerary(null);
                $('#route-detail-summary').html(
                    '<p class="muted-text">Could not calculate route details.</p>'
                );
            });
    }

    // -----------------------------------------------
    // Reorder & Remove
    // -----------------------------------------------

    function moveStop(index, direction) {
        var newIndex = index + direction;
        if (newIndex < 0 || newIndex >= stops.length) return;

        var temp = stops[index];
        stops[index] = stops[newIndex];
        stops[newIndex] = temp;

        sessionStorage.setItem('sidequest_stops', JSON.stringify(stops));
        placeMarkers();
        fetchLegs();
    }

    function removeStop(index) {
        stops.splice(index, 1);
        sessionStorage.setItem('sidequest_stops', JSON.stringify(stops));

        if (!stops.length) {
            window.location.href = '/';
            return;
        }

        placeMarkers();
        fetchLegs();
    }

    // -----------------------------------------------
    // Apple Maps export
    // -----------------------------------------------

    function updateAppleMapsLink() {
        var saddr = routeData.start.lat + ',' + routeData.start.lon;
        var daddr = stops.map(function(s) { return s.lat + ',' + s.lon; }).join('+to:');
        daddr += '+to:' + routeData.end.lat + ',' + routeData.end.lon;

        $('#apple-maps-link').attr('href',
            'https://maps.apple.com/?saddr=' + saddr + '&daddr=' + daddr + '&dirflg=d'
        );
    }

    // -----------------------------------------------
    // Boot
    // -----------------------------------------------

    fetchLegs();
}
