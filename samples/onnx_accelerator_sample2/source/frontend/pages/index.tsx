// Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
// Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import type {NextPage} from 'next';
import TopBar from "../components/TopBar";
import Main from '../components/Main'

import {Authenticator} from '@aws-amplify/ui-react';

const Home: NextPage = () => {
    return (
        <Authenticator hideSignUp>
            {({signOut, user}) => (
                <div>
                    <TopBar signOut={signOut} user={user}/>
                    <Main/>
                </div>
            )}
        </Authenticator>
    )
}

export default Home
