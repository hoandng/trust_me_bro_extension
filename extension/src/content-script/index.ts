import { ExtensionMessage } from '../shared/types';

console.log('Hello world from content script on Facebook!');

const msg: ExtensionMessage = {
  type: 'ANALYZE_POST',
  payload: {
    postId: '123',
    content: 'Hello Facebook'
  }
};
console.log('Sending message:', msg);
