import axios from "axios";

import { API_BASE } from './apiConfig';

export default axios.create({
    baseURL: API_BASE
});