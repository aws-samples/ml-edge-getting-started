// Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
// Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import ImageCanvas from "./ImageCanvas";

function App(props) {
    return (
        <div className="App mainContainer">
            <ImageCanvas width={240} height={240}/>
        </div>
    );
}

export default App;