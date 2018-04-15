import Component from '@ember/component';

export default Component.extend({
  classNames: 'chat-pane',

  _sendChat(text) {
    const action = this.get('sendChat');

    if (text && typeof action === 'function') {
      action(text);
      this.set('chatMessage', '');
    }
  }
});
