#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { QuizStack } from '../lib/base/quiz-stack';

const app = new cdk.App();
const env = app.node.tryGetContext("env")
const config = app.node.tryGetContext(env)

new QuizStack(app, 'QuizStack', {
  env: {
    account: config.account,
    region: config.region,
  },
  environment: env,
  hostedZoneId: config.hostedZoneId,
});
