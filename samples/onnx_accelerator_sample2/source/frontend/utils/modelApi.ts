import { Auth, API } from "aws-amplify";

export function downloadBlob(url:string, filename:string) {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || 'download';
    const clickHandler = () => {
      setTimeout(() => {
        URL.revokeObjectURL(url);
        a.removeEventListener('click', clickHandler);
      }, 150);
    };
    a.addEventListener('click', clickHandler, false);
    a.click();
    return a;
  }

export async function fetchLatestModelFromS3() {

    // let's get the cognito token
    const currentSession = await Auth.currentSession();

    const token = currentSession.getIdToken().getJwtToken();
    
    const requestData = {
        headers: {
          Authorization: token
        }
      }

    // now we can get the presigned url from S3
    const data = await API.get('codesamplebackendapi', '/getmodelurl', requestData)

    // let's call that presigned url to download the model
    downloadBlob(data['download_url'], data['filename'])
    
  }