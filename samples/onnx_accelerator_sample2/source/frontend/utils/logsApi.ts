import { Auth, API } from "aws-amplify";

export async function uploadLogs(inferenceResponse: any, s3UploadResponse: any, selectedModel: any) {

    // let's get the cognito token

    const currentSession = await Auth.currentSession();

    const token = currentSession.getIdToken().getJwtToken();
    
    const requestData = {
        body: {
          ts: new Date().getTime().toLocaleString(),
          label: inferenceResponse[0].label,
          score: inferenceResponse[0].score,
          inputImageUrl: s3UploadResponse.url,
          inputImageKey: s3UploadResponse.fields['key'],
          modelName: selectedModel.name
        },
        headers: {
          Authorization: token
        }
      }

    // now we can post the logs to be ingested by a lambda function
    const data = await API.post('codesamplebackendapi', '/postlogs', requestData);
    
  }