// jshint esversion: 6
'use strict';

// -------------------------------------------------------------------------------------------------------------------
// Auth
// -------------------------------------------------------------------------------------------------------------------

function authLogin() {
	const form = document.getElementById('login-form');
	const data = new FormData(form);

	$.ajax({
		type: 'POST',
		url: '/account/login',
		data: data,
		processData: false,
		contentType: false,
	}).done(function(res) {
		document.getElementById('login-error').textContent = '';
		document.getElementById('user-name').textContent = res.first_name;
		document.body.classList.add('authenticated');
		form.reset();
	}).fail(function(xhr) {
		const errors = xhr.responseJSON || {};
		const first = Object.values(errors)[0];
		document.getElementById('login-error').textContent = (first && first[0]) || 'Login failed';
	});
}

function authLogout() {
	$.ajax({
		type: 'POST',
		url: '/account/logout',
	}).done(function() {
		document.getElementById('user-name').textContent = '';
		document.body.classList.remove('authenticated');
	}).fail(ajaxFailure);
}
