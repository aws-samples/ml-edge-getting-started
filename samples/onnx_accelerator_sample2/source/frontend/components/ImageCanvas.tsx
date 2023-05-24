// Original Copyright Microsoft Corporation. Licensed under the MIT License.
// Modifications Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
// Licensed under the Amazon Software License  http://aws.amazon.com/asl/

// 2022-08-19: Amazon addition.
import {useRef, useState, useEffect} from 'react';
import {analyzeImage} from '../utils/predict';
import {createInferenceSession} from '../utils/modelHelper';
import {fetchLatestModelFromS3} from '../utils/modelApi';
import {uploadImageToS3} from '../utils/imageApi';
import {uploadLogs} from '../utils/logsApi';
import InputGroup from 'react-bootstrap/InputGroup';
import Form from 'react-bootstrap/Form';
import Button from 'react-bootstrap/Button';
import Stack from 'react-bootstrap/Stack';
import Table from 'react-bootstrap/Table';
import FloatingLabel from 'react-bootstrap/FloatingLabel';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
// End of Amazon addition.

interface Props {
    height: number;
    width: number;
}

const ImageCanvas = (props: Props) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    // 2022-08-19: Amazon addition.
    const [selectedImage, setSelectedImage] = useState<any>(null);
    const [selectedImageUrl, setSelectedImageUrl] = useState<any>(null);
    const [selectedModel, setSelectedModel] = useState<any>(null);

    const [inferenceResponse, setInferenceResponse] = useState<any>(null);

    useEffect(() => {
        if (selectedImage != null) {
            const objectUrl = URL.createObjectURL(selectedImage)
            console.log(`Image file uri: ${objectUrl}`)
            setSelectedImageUrl(objectUrl);

            let image: HTMLImageElement = new Image();
            image.src = objectUrl
    // End of Amazon addition.

            const canvas = canvasRef.current;
            const ctx = canvas!.getContext('2d');
            image.onload = () => {
                ctx!.drawImage(image, 0, 0, props.width, props.height);
            }

    // 2022-08-19: Amazon addition.
        }
    }, [selectedImage, props.width, props.height])

    useEffect(() => {
        if (selectedModel != null) {
            const objectUrl = URL.createObjectURL(selectedModel)
            console.log(`Model file uri: ${objectUrl}`)

            createInferenceSession(objectUrl)
        }
    }, [selectedModel])

    const updateImage = (event: any) => {
        if (event.target.files) {
            if (event.target.files[0]) {
                const i = event.target.files[0];

                console.log('Image file selected');
                console.log(i);

                setSelectedImage(i);
            } else {
                console.log('No image file selected')

                setSelectedImage(null)
                setSelectedImageUrl(null)
            }

            setInferenceResponse(null)
        }
    };

    const updateModel = (event: any) => {
        if (event.target.files) {
            if (event.target.files[0]) {
                const i = event.target.files[0];

                console.log('Model file selected')
                console.log(i)

                setSelectedModel(i);

            } else {
                console.log('No model file selected')

                setSelectedModel(null)
            }

            setInferenceResponse(null)
        }
    };

    const missingRequiredInput = () => {
        return !selectedImageUrl || !selectedModel
    }

    const submit = async () => {
        const inferenceResponse = await analyzeImage(selectedImageUrl);

        const formattedResponse = inferenceResponse
            .filter((item: any) => (item.response[0]).length > 0)
            .map(function (item: any) {
                const [inferenceResult, inferenceTime] = item.response;

                // Get the highest confidence result
                const topResult = inferenceResult[0];

                return {
                    type: item.type,
                    label: topResult.name.toUpperCase(),
                    score: topResult.probability,
                    time: inferenceTime
                }
            });

        console.log(formattedResponse)

        setInferenceResponse(formattedResponse)

        const uploadResponse = await uploadImageToS3(selectedImageUrl);
        uploadLogs(formattedResponse, uploadResponse, selectedModel);
    };

    return (
        <div>
            <InputGroup>
                <Stack>
                    <Form.Group className="mb-3">
                        <Form.Label>Select model</Form.Label>
                        <Form.Control type="file" onChange={updateModel} accept=".onnx"/>
                    </Form.Group>
                    <Form.Group className="mb-3">
                        <Form.Label>Select image</Form.Label>
                        <Form.Control type="file" onChange={updateImage} accept="image/*"/>
                    </Form.Group>
                    <Button variant="primary" className="mb-3" type="submit"
                            onClick={fetchLatestModelFromS3}>
                        Get latest model
                    </Button>
                    <Button disabled={missingRequiredInput()} variant="primary" className="mb-3" type="submit"
                            onClick={submit}>
                        Analyze image
                    </Button>
                    <div className="container-canvas mb-3">
                        <canvas ref={canvasRef} width={props.width} height={props.height}/>
                    </div>

                    {inferenceResponse && (
                        <div>
                            <div className="mb-3">
                                <Form.Group as={Row} className="inference-result">
                                    <Form.Label column sm="2" className="fw-bold">Label</Form.Label>
                                    <Col sm="10">
                                        <Form.Control plaintext readOnly value={inferenceResponse[0].label}/>
                                    </Col>
                                </Form.Group>
                                <Form.Group as={Row} className="inference-result">
                                    <Form.Label column sm="2" className="fw-bold">Score</Form.Label>
                                    <Col sm="10">
                                        <Form.Control plaintext readOnly value={inferenceResponse[0].score}/>
                                    </Col>
                                </Form.Group>
                            </div>
                            <Table className="mb-3">
                                <thead>
                                <tr>
                                    <th>Runtime Type</th>
                                    <th>Inference Time</th>
                                </tr>
                                </thead>
                                <tbody>
                                {inferenceResponse.map((item: any) => (
                                    <tr key={item.type + new Date()}>
                                        <td>{item.type}</td>
                                        <td>{item.time}</td>
                                    </tr>
                                ))}
                                </tbody>
                            </Table>
                        </div>
                    )}
                </Stack>
            </InputGroup>
        </div>
    );
    // End of Amazon addition.
};

export default ImageCanvas;
