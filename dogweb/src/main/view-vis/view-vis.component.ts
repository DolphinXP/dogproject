import {Component, ElementRef, inject, ViewChild} from '@angular/core';
import {VisService} from '../../service/vis.service';

@Component({
  selector: 'app-view-vis',
  imports: [],
  templateUrl: './view-vis.component.html',
  styleUrl: './view-vis.component.css'
})
export class ViewVisComponent {
  @ViewChild('statusIndicator') statusIndicator!: ElementRef;
  @ViewChild('videoElement') videoElement!: ElementRef<HTMLVideoElement>;
  @ViewChild('videoInfo') videoInfo!: ElementRef;
  @ViewChild('logElement') logElement!: ElementRef;

  private streamService = inject(VisService);

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
