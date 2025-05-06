import {Injectable} from '@angular/core';
import {ResourceUsage} from '../domain/resource-usage';

@Injectable({
  providedIn: 'root'
})
export class MainService {

  serviceUrl = 'http://31.41.59.100:8080';

  constructor() {
  }

  setServiceUrl(url: string) {
    this.serviceUrl = url;
  }

  resourceUsageWebSocket(signalCallback: (data: ResourceUsage) => void) {
    const ws = new WebSocket(`ws://${this.serviceUrl.replace(/^https?:\/\//, '')}/resource_usage`);
    ws.onmessage = (event) => {
      const data: ResourceUsage = JSON.parse(event.data);
      signalCallback(data);
    };
    ws.onerror = (error) => {
      console.error('Resource usage WebSocket error:', error);
    };
    ws.onclose = () => {
      console.log('Resource usage WebSocket connection closed');
    };
    return ws;
  }

}
