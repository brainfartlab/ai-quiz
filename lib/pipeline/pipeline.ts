import { Arn, ArnFormat, Stack, StackProps } from 'aws-cdk-lib';
import { CodePipeline, CodePipelineSource, ShellStep } from 'aws-cdk-lib/pipelines';
import { Construct } from 'constructs';

import { PipelineStage } from './stage';

interface PipelineStackProps extends StackProps {
  account: string,
  branch: 'dev' | 'main';
  environment: 'dev' | 'prd';
  repoName: string;
}

export class PipelineStack extends Stack {
  constructor(scope: Construct, id: string, props: PipelineStackProps) {
    super(scope, id, props);

    const pipeline = new CodePipeline(this, 'QuizPipeline', {
      crossAccountKeys: true,
      synth: new ShellStep('Synth', {
        input: CodePipelineSource.connection(props.repoName, props.branch, {
          connectionArn: Arn.format({
            arnFormat: ArnFormat.SLASH_RESOURCE_NAME,
            resource: 'connection',
            resourceName: 'f8eceddd-62d2-4af2-91bb-c2ea0555ec36',
            service: 'codestar-connections',
          }, this),
        }),
        commands: [
          'npm ci',
          'npm run build',
          'npx cdk synth --app \'npx ts-node --prefer-ts-exts bin/pipeline.ts\'',
        ],
      }),
    });

    pipeline.addStage(new PipelineStage(this, props.environment, {
      env: {
        account: props.account,
        region: 'eu-west-1',
      },
      environment: props.environment,
    }));
  }
}
