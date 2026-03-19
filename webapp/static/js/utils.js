// jshint esversion: 6
'use strict';

// -------------------------------------------------------------------------------------------------------------------
// CSRF
// -------------------------------------------------------------------------------------------------------------------

$.ajaxSetup({
	beforeSend: function(xhr, settings) {
		if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type)) {
			xhr.setRequestHeader('X-CSRFToken', $('meta[name="csrf-token"]').attr('content'));
		}
	}
});

// -------------------------------------------------------------------------------------------------------------------
// AJAX Utilities
// -------------------------------------------------------------------------------------------------------------------

const postJson = (url, json) => {
	return $.ajax({
		type: "POST",
		url: url,
		contentType: "application/json",
		data: JSON.stringify(json)
	});
};

const ajaxFailure = (data, status, error) => {
	console.error('Ajax Error:', error, data.responseText);
	alert(`Error: ${error}\n${data.responseText}`);
};
