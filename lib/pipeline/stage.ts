import { Stage, StageProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';

import { QuizStack } from '../base/quiz-stack';

interface PipelineStageProps extends StageProps {
  environment: 'tst' | 'dev' | 'prd';
}

export class PipelineStage extends Stage {
  constructor(scope: Construct, id: string, props: PipelineStageProps) {
    super(scope, id, props);

    new QuizStack(this, 'QuizStack', {
      environment: props.environment,
    });
  }
}
