import * as cdk from 'aws-cdk-lib';
import * as pythonLambda from '@aws-cdk/aws-lambda-python-alpha';
import { Construct } from 'constructs';

import { Cache } from '../constructs/cache';
import { Data } from '../constructs/data';
import { ChatMemory } from '../constructs/memory';
import { Routing } from '../constructs/routing';
import { Api } from '../backend/api';
import { Common } from '../backend/common';
import { GameFlow } from '../backend/gameflow';

interface QuizStackProps extends cdk.StackProps {
  environment: 'dev' | 'prd' | 'tst';
  hostedZoneId: string;
  netlifyDomain?: string;
}

export class QuizStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: QuizStackProps) {
    super(scope, id, props);

    const data = new Data(this, 'DataStorage', {
      retainData: props.environment === 'prd',
    });
    const cache = new Cache(this, 'Cache', {
      retainData: props.environment === 'prd',
    });

    const origin = props.environment === 'tst' ? 'http://localhost:1234' : `https://quiz.${props.environment}.brainfartlab.com`;

    const commonFunctionality = new Common(this, 'CommonFunctionality');

    const gameFlow = new GameFlow(this, 'GameFlow', {
      commonLayer: commonFunctionality.commonLayer,
      gameTable: data.gameTable,
      questionTable: data.questionTable,
    });

    const quizApi = new Api(this, 'QuizApi', {
      commonLayer: commonFunctionality.commonLayer,
      gameFlowQueue: gameFlow.gameFlowQueue,
      gameTable: data.gameTable,
      origin,
      questionTable: data.questionTable,
      tokenTable: cache.tokenTable,
    });

    new Routing(this, 'Routing', {
      api: quizApi.api,
      hostedZoneId: props.hostedZoneId,
      netlifyDomain: props.netlifyDomain,
      path: 'quiz/v1',
      environment: props.environment,
      stage: quizApi.stage,
    });
  }
}
