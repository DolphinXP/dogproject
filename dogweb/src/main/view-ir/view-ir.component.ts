import {Component, ElementRef, inject, ViewChild} from '@angular/core';
import {IrService} from '../../service/ir.service';

@Component({
  selector: 'app-view-ir',
  imports: [],
  templateUrl: './view-ir.component.html',
  styleUrl: './view-ir.component.css'
})
export class ViewIrComponent {
  @ViewChild('statusIndicator') statusIndicator!: ElementRef;
  @ViewChild('videoElement') videoElement!: ElementRef<HTMLVideoElement>;
  @ViewChild('videoInfo') videoInfo!: ElementRef;
  @ViewChild('logElement') logElement!: ElementRef;

  private streamService = inject(IrService);

  constructor() {

  }

  ngAfterViewInit() {
    // 传递元素引用给服务
    this.streamService.videoElement = this.videoElement;
    this.streamService.logElement = this.logElement;
    this.streamService.statusIndicator = this.statusIndicator;
    this.streamService.videoInfo = this.videoInfo;
    
    this.streamService.reinitializeStream();
  }


  preventPause(event: MouseEvent) {
    event.preventDefault();
    event.stopPropagation();
    // 立即播放，防止暂停
    const video = event.target as HTMLVideoElement;
    if (video.paused) {
      video.play();
    }
  }

  disableContextMenu(event: MouseEvent) {
    event.preventDefault();
  }
}
