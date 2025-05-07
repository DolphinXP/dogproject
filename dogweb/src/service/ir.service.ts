import {Injectable} from '@angular/core';
import {WebrtcService} from './webrtc.service';

@Injectable({
  providedIn: 'root'
})
export class IrService extends WebrtcService {
  override serviceUrl = 'http://31.41.59.100:8082';


  constructor() {
    super();
    console.log(`IrService initialized, mobile: ${this.isMobile}`);
  }
  
}
