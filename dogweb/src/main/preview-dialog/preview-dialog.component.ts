import {Component, ElementRef, inject, ViewChild} from '@angular/core';
import {Dialog} from 'primeng/dialog';
import {DetectInfo} from '../../domain/detect-info';
import {MainService} from '../../service/main.service';
import {Button} from 'primeng/button';

@Component({
  selector: 'app-preview-dialog',
  imports: [
    Dialog,
    Button
  ],
  templateUrl: './preview-dialog.component.html',
  styleUrl: './preview-dialog.component.css'
})
export class PreviewDialogComponent {
  title = '';
  visible = false;
  videoUrl = '';

  @ViewChild('videoPlayer') videoPlayer!: ElementRef<HTMLVideoElement>;

  mainService = inject(MainService);

  showDialog(item: DetectInfo) {
    if (this.videoPlayer) {
      this.title = item.name;
      this.videoUrl = this.mainService.getRemoteUrl(item.videoUrl);
      this.videoPlayer.nativeElement.load();
      this.visible = true;
    }
  }

// Option 2: If the server supports it, you can add a download attribute
  saveVideo() {
    const link = document.createElement('a');
    link.href = this.videoUrl.replace(/detected/gi, 'detected_download');
    link.setAttribute('download', this.title || 'video.mp4');
    link.setAttribute('target', '_blank');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}
