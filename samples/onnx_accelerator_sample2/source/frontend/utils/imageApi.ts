import { Auth, API } from "aws-amplify";
import Jimp from 'jimp';
import {loadImageFromPathNoResize} from './imageHelper';
import { Blob } from "buffer";

async function postFileToS3(presignedPostData: any, file: Jimp) {
      const formData = new FormData();
      Object.keys(presignedPostData.fields).forEach(key => {
        formData.append(key, presignedPostData.fields[key]);
      });
      // Actual file has to be appended last.
      const bufferData = await file.getBufferAsync('image/jpeg');
      const blob = new globalThis.Blob([bufferData]);
      formData.append("file", blob);
      const xhr = new XMLHttpRequest();
      xhr.open("POST", presignedPostData.url, true);
      xhr.send(formData);
  };

export async function uploadImageToS3(imagePath: string) {

    // let's get the cognito token
    const currentSession = await Auth.currentSession();

    const token = currentSession.getIdToken().getJwtToken();
    
    const requestData = {
        headers: {
          Authorization: token
        }
      }

    // now we can get the presigned url from S3 to upload our object
    const data = await API.get('codesamplebackendapi', '/getuploadurl', requestData);

    // let's call that presigned url to upload the image
    var imageData = await loadImageFromPathNoResize(imagePath);
    postFileToS3(data, imageData);

    return data;
  }