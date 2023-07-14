#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { PipelineStack } from '../lib/pipeline/pipeline';

const app = new cdk.App();
const env = 'dev';
const config = app.node.tryGetContext(env);

new PipelineStack(app, 'ai-quiz-dev-pipeline', {
  env: {
    account: '799425856515',
    region: 'eu-west-1',
  },
  account: config.account,
  branch: 'dev',
  environment: env,
  repoName: 'brainfartlab/ai-quiz',
});
