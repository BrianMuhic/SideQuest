// jshint esversion: 6
'use strict';

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
