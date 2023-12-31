import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';

import { Data } from '../constructs/data';
import { ChatMemory } from '../constructs/memory';
import { Routing } from '../constructs/routing';
import { Api } from '../backend/api';

interface QuizStackProps extends cdk.StackProps {
  environment: 'dev' | 'prd' | 'tst';
}

export class QuizStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: QuizStackProps) {
    super(scope, id, props);

    const chatMemory = new ChatMemory(this, 'ChatMemory', {
      retainData: props.environment === 'prd',
    });
    const data = new Data(this, 'DataStorage', {
      retainData: props.environment === 'prd',
    });

    const quizApi = new Api(this, 'QuizApi', {
      gameTable: data.gameTable,
      memoryTable: chatMemory.memoryTable,
      questionTable: data.questionTable,
    });

    new Routing(this, 'Routing', {
      api: quizApi.api,
      path: 'quiz/v1',
      environment: props.environment,
      stage: quizApi.stage,
    });
  }
}
