// jshint esversion: 6
'use strict';

// -------------------------------------------------------------------------------------------------------------------
// Auth
// -------------------------------------------------------------------------------------------------------------------

let authActiveTab = 'login';

function authTab(tab) {
	authActiveTab = tab;
	document.getElementById('tab-login').classList.toggle('active', tab === 'login');
	document.getElementById('tab-register').classList.toggle('active', tab === 'register');
	document.getElementById('login-form').style.display = tab === 'login' ? '' : 'none';
	document.getElementById('register-form').style.display = tab === 'register' ? '' : 'none';
	document.getElementById('auth-btn').textContent = tab === 'login' ? 'Sign in' : 'Sign up';
	document.getElementById('login-error').textContent = '';
	document.getElementById('register-error').textContent = '';
}

function authSubmit() {
	if (authActiveTab === 'login') authLogin();
	else authRegister();
}

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
		document.getElementById('user-name').textContent = res.username;
		document.body.classList.add('authenticated');
		form.reset();
	}).fail(function(xhr) {
		const errors = xhr.responseJSON || {};
		const first = Object.values(errors)[0];
		document.getElementById('login-error').textContent = (first && first[0]) || 'Login failed';
	});
}

function authRegister() {
	const form = document.getElementById('register-form');
	const data = new FormData(form);

	$.ajax({
		type: 'POST',
		url: '/account/register',
		data: data,
		processData: false,
		contentType: false,
	}).done(function(res) {
		document.getElementById('user-name').textContent = res.username;
		document.body.classList.add('authenticated');
		form.reset();
		authTab('login');
	}).fail(function(xhr) {
		const errors = xhr.responseJSON || {};
		const first = Object.values(errors)[0];
		document.getElementById('register-error').textContent = (first && first[0]) || 'Registration failed';
	});
}

function authLogout() {
	$.ajax({
		type: 'POST',
		url: '/account/logout',
	}).done(function() {
		document.getElementById('user-name').textContent = '';
		document.body.classList.remove('authenticated');
		authTab('login');
	}).fail(ajaxFailure);
}
