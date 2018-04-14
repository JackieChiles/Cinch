const { Builder, By } = require('selenium-webdriver');

const southDriver = new Builder()
  .forBrowser('chrome')
  .build();

southDriver.get('http://localhost:4200/home')
  .then(() => southDriver.findElement(By.css('md-checkbox')).click())
  .then(() => southDriver.findElement(By.css('.main-toolbar .new-link')).click())
  .then(() => southDriver.findElement(By.css('button.md-accent')).click());

const westDriver = new Builder()
  .forBrowser('chrome')
  .build();

westDriver.get('http://localhost:4200/home')
  .then(() => westDriver.findElement(By.css('md-checkbox')).click())
  .then(() => westDriver.findElement(By.css('.main-toolbar .games-link')).click())
  .then(() => westDriver.findElement(By.css('md-sidenav md-list-item:last-of-type')).click())
  .then(() => westDriver.findElement(By.css('.east-west-seats div:first-child .join-button')).click());

const northDriver = new Builder()
  .forBrowser('chrome')
  .build();

northDriver.get('http://localhost:4200/home')
  .then(() => northDriver.findElement(By.css('md-checkbox')).click())
  .then(() => northDriver.findElement(By.css('.main-toolbar .games-link')).click())
  .then(() => northDriver.findElement(By.css('md-sidenav md-list-item:last-of-type')).click())
  .then(() => northDriver.findElement(By.css('.north-seat div:first-child .join-button')).click());

const eastDriver = new Builder()
  .forBrowser('chrome')
  .build();

eastDriver.get('http://localhost:4200/home')
  .then(() => eastDriver.findElement(By.css('md-checkbox')).click())
  .then(() => eastDriver.findElement(By.css('.main-toolbar .games-link')).click())
  .then(() => eastDriver.findElement(By.css('md-sidenav md-list-item:last-of-type')).click())
  .then(() => eastDriver.findElement(By.css('.east-west-seats div:last-child .join-button')).click());
