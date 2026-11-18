# Lab: Reflected XSS into HTML context with nothing encoded
level: apprentice

## Description

This lab contains a simple reflected cross-site scripting vulnerability in the search functionality.

To solve the lab, perform a cross-site scripting attack that calls the alert function.

# Solution

Payload: `<script>alert(1)</script>`

![fig.png](fig.png)
