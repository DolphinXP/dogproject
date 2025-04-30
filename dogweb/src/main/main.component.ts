import {Component, inject} from '@angular/core';
import {SidePanelComponent} from './side-panel/side-panel.component';
import {ViewVisComponent} from './view-vis/view-vis.component';
import {ViewIrComponent} from './view-ir/view-ir.component';
import {NgClass} from '@angular/common';
import {VisService} from '../service/vis.service';
import {IrService} from '../service/ir.service';
import {Toast} from 'primeng/toast';
import {MessageService} from 'primeng/api';

@Component({
  selector: 'app-main',
  imports: [
    SidePanelComponent,
    ViewVisComponent,
    ViewIrComponent,
    NgClass,
    Toast
  ],
  providers: [MessageService],
  templateUrl: './main.component.html',
  styleUrl: './main.component.css'
})
export class MainComponent {
// @ViewChild('videoBackdrop') videoBackdrop!: ElementRef<HTMLVideoElement>;

  isIrMain = false;

  private visService = inject(VisService);
  private irService = inject(IrService);
  private msgService = inject(MessageService);


  // setMediaStream(stream: MediaStream | null) {
  //   if (this.videoBackdrop) {
  //     this.videoBackdrop.nativeElement.srcObject = stream;
  //   }
  // }

  toggleView(event: MouseEvent) {
    const target = event.currentTarget as HTMLElement;
    if (target.classList.contains('sub-view')) {
      this.isIrMain = !this.isIrMain;
      // if (this.isIrMain) {
      //   this.setMediaStream(this.irService.mediaStream);
      // } else {
      //   this.setMediaStream(this.visService.mediaStream);
      // }
    }
  }
}
