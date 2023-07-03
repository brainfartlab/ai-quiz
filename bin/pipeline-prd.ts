#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { PipelineStack } from '../lib/pipeline/pipeline';

const app = new cdk.App();
new PipelineStack(app, 'ai-quiz-prd-pipeline', {
  env: {
    account: '799425856515',
    region: 'eu-west-1',
  },
  account: '710339506557',
  branch: 'main',
  environment: 'prd',
  repoName: 'brainfartlab/ai-quiz',
});
