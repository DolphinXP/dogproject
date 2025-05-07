import {Injectable} from '@angular/core';
import {WebrtcService} from './webrtc.service';

@Injectable({
  providedIn: 'root'
})
export class VisService extends WebrtcService {
  override serviceUrl = 'http://31.41.59.100:8081';

  constructor() {
    super();
    console.log(`VisService initialized, mobile: ${this.isMobile}`);
  }

}
