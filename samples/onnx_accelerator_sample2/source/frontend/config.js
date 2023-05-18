/*
 * Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
 * Licensed under the Amazon Software License  http://aws.amazon.com/asl/
*/

// https://docs.amplify.aws/lib/client-configuration/configuring-amplify-categories/q/platform/js/

const config = {
  Auth: {
    region: process.env.NEXT_PUBLIC_REGION_NAME,
    userPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID,
    userPoolWebClientId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_CLIENT_ID,
    identityPoolId: process.env.NEXT_PUBLIC_COGNITO_IDENTITY_POOL_ID
  },
  API: {
    endpoints: [
      {
        name: "codesamplebackendapi",
        endpoint: process.env.NEXT_PUBLIC_API_GATEWAY_ENDPOINT
      }
    ]
  }
};

export default config;
