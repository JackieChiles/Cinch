import Service from '@ember/service';

export default Service.extend({
  // Returns the value under the given key from local storage
  getValue(key) {
    return localStorage.getItem(key);
  },

  // Stores the value under the given key in local storage
  stashValue(key, value) {
    localStorage.setItem(key, value);
  },

  clearValue(key) {
    localStorage.removeItem(key);
  }
});
