import http from 'k6/http';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';
//import { writeFileSync, appendFileSync } from 'fs';


const gatewayUrl = __ENV.GATEWAY_URL; // Access the environment variable
const url = `http://${gatewayUrl}/productpage`; // Construct the URL

// Temporary files to store the results during execution
const DURATION_FILE = 'durations_temp.json';
const ERROR_FILE = 'errors_temp.json';
// Function to append results to a temporary file
function appendResultToFile(fileName, data) {
    try {
        appendFileSync(fileName, JSON.stringify(data) + '\n');
    } catch (err) {
        console.error(`Error writing to file ${fileName}: ${err}`);
    }
}


export const options = {
  discardResponseBodies: true,
  scenarios: {
    warmup: {
      executor: 'constant-arrival-rate',

      // How long the warmup lasts
      duration: '5m',  // Warm-up duration (adjust as needed)

      // How many iterations per timeUnit
      rate: 20,  // Warm-up rate in QPS

      // Start `rate` iterations per second
      timeUnit: '1s',

      // Pre-allocate VUs before starting the warm-up
      preAllocatedVUs: 1500,  // Fewer VUs needed for warm-up

      // Maximum VUs to sustain the defined constant arrival rate.
      maxVUs: 5000,
    },

    contacts: {
      executor: 'constant-arrival-rate',

      // How long the test lasts
      duration: '20m',

      // How many iterations per timeUnit
      rate: 100,

      // Start `rate` iterations per second
      timeUnit: '1s',

      // Pre-allocate VUs before starting the test
      preAllocatedVUs: 7000,

      // Spin up a maximum VUs to sustain the defined
      // constant arrival rate.
      maxVUs: 50000,

      // Ensure this scenario starts after the warmup completes
      startTime: '5m',  // Starts after the warm-up scenario ends
    },
  },
};

export default function () {
  let startTime = new Date().toISOString(); // Capture the time when the request is sent
  let res = http.get(url);
  if (Math.random() <= 1/100) {
    
    console.log(`Request sent at ${startTime} with duration ${res.timings.duration} ms`);
  }
	  // Append request duration to the temporary file
//    appendResultToFile(DURATION_FILE, {
//        time: startTime,
//        duration: res.timings.duration
//    });

    // If there's an error, append it to the error file
//    if (res.status !== 200) {
//        appendResultToFile(ERROR_FILE, {
//            time: startTime,
//            error: res.status
//        });
//    }
}

//export function handleSummary(data) {
//    // Read and consolidate results from temporary files
//    let durations = [];
//    let errors = [];

    // Read duration data
//    try {
//        let lines = readFileSync(DURATION_FILE, 'utf-8').split('\n').filter(Boolean);
//        durations = lines.map(JSON.parse);
//    } catch (err) {
//        console.error(`Error reading from file ${DURATION_FILE}: ${err}`);
//    }

    // Read error data
//    try {
//        let lines = readFileSync(ERROR_FILE, 'utf-8').split('\n').filter(Boolean);
//        errors = lines.map(JSON.parse);
//    } catch (err) {
//        console.error(`Error reading from file ${ERROR_FILE}: ${err}`);
//    }

//    let output = {
//        durations: requestDurations,
//        errors: requestErrors
//    };
//    console.log("Durations Array:", JSON.stringify(requestDurations));
//    console.log("Errors Array:", JSON.stringify(requestErrors));

//    return {
//        'result.json': JSON.stringify(output, null, 2), // Export the data as a JSON file
//        'stdout': textSummary(data, { indent: ' ', enableColors: true }),
//    };
//}
