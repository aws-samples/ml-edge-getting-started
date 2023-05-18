// Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
// Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import React from 'react';
import {Navbar, Container, Button} from 'react-bootstrap';

function TopBar({signOut, user}: any) {
    return (
        <Navbar bg="light" expand="lg" className="gradient">
            <Container>
                <Navbar.Brand className="logo">AWS Samples</Navbar.Brand>
                <Button variant="light" onClick={() => {signOut()}}>Logout</Button>
            </Container>
        </Navbar>
    );
}

export default TopBar;