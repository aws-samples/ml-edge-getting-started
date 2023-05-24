// Original Copyright Microsoft Corporation. Licensed under the MIT License.
// Modifications Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
// Licensed under the Amazon Software License  http://aws.amazon.com/asl/

// 2022-08-19: Amazon addition.
import 'bootstrap/dist/css/bootstrap.min.css';
import "../styles/app.scss";
import '@aws-amplify/ui-react/styles.css';
import {Amplify} from 'aws-amplify';
import config from '../config';
// End of Amazon addition.

import type { AppProps } from 'next/app'

// 2022-08-19: Amazon addition.
Amplify.configure({
  ... config, ssr: true
});
// End of Amazon addition.

function MyApp({ Component, pageProps }: AppProps) {
  const AnyComponent = Component as any;

  // 2022-08-19: Amazon addition.
  return <AnyComponent {...pageProps} />
  // End of Amazon addition.
}
export default MyApp
