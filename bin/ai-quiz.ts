#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { QuizStack } from '../lib/base/quiz-stack';

const app = new cdk.App();
new QuizStack(app, 'QuizStack', {
  env: {
    account: '811733000668',
    region: 'eu-west-1',
  },
  environment: 'tst'
});
