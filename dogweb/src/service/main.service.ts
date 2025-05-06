import {Injectable} from '@angular/core';
import {ResourceUsage} from '../domain/resource-usage';
import {TaskInfo} from '../domain/task-info';
import {DetectInfo} from '../domain/detect-info';

@Injectable({
  providedIn: 'root'
})
export class MainService {

  serviceUrl = 'http://31.41.59.100:8080';
  currentTaskInfo: TaskInfo | null = null;


  setServiceUrl(url: string) {
    this.serviceUrl = url;
  }

  setCurrentTaskInfo(taskInfo: TaskInfo) {
    this.currentTaskInfo = taskInfo;
  }

  getRemoteUrl(url: string) {
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url;
    } else {
      return `${this.serviceUrl}/${url}`;
    }
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

  detectedCompactWebSocket(signalCallback: (data: DetectInfo[]) => void) {
    const ws = new WebSocket(`ws://${this.serviceUrl.replace(/^https?:\/\//, '')}/detected_compact`);
    ws.onmessage = (event) => {
      const data: DetectInfo[] = JSON.parse(event.data);
      signalCallback(data);
    };
    ws.onerror = (error) => {
      console.error('Detect info compact WebSocket error:', error);
    };
    ws.onclose = () => {
      console.log('Detect info compact WebSocket connection closed');
    };
    return ws;
  }

}
